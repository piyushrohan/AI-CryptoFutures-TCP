"""Deterministic in-memory paper exchange.

This service simulates local paper order handling only. It does not connect to
Binance, sign requests, submit venue orders, or model production-grade matching.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from libs.schemas import (
    AccountState,
    ExpectedEdgeBreakdown,
    FeePolicy,
    Freshness,
    InstrumentRole,
    OrderSide,
    OrderStatus,
    PaperFill,
    PaperMarketQuote,
    PaperOrder,
    PaperOrderIntent,
    PaperOrderPreview,
    ReconciliationEvent,
    ReconciliationStatus,
    SymbolMetadata,
    TimeInForce,
    decimal_str,
    default_account_state,
    now_utc,
)
from services.portfolio import apply_paper_fill, portfolio_payload
from services.execution import validate_maker_first_intent
from services.paper_exchange.persistence import PaperExchangeStateStore
from services.risk import PaperRiskResult, PaperRiskState, evaluate_paper_order_risk


PAPER_SOURCE = "local_paper_simulator"


@dataclass(frozen=True)
class PaperSubmitResult:
    accepted: bool
    preview: PaperOrderPreview
    order: PaperOrder | None
    reconciliation_event: ReconciliationEvent
    risk_result: PaperRiskResult | None = None

    def to_public_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "preview": self.preview.to_public_dict(),
            "risk": (
                self.risk_result.to_public_dict() if self.risk_result else None
            ),
            "order": self.order.to_public_dict() if self.order else None,
            "reconciliation_event": self.reconciliation_event.to_public_dict(),
            "execution": "paper_only",
        }


def _freshness(reference_time: datetime) -> Freshness:
    return Freshness(
        source=PAPER_SOURCE,
        source_timestamp=reference_time,
        received_timestamp=reference_time,
    )


def _default_quotes(reference_time: datetime) -> dict[str, PaperMarketQuote]:
    return {
        "BTCUSDC": PaperMarketQuote(
            symbol="BTCUSDC",
            best_bid=Decimal("65000.0"),
            best_ask=Decimal("65000.5"),
            bid_size=Decimal("4.2"),
            ask_size=Decimal("3.8"),
            mark_price=Decimal("65000.25"),
            funding_rate_bps=Decimal("0.8"),
            short_horizon_volatility_bps=Decimal("12"),
            freshness=_freshness(reference_time),
        ),
        "ETHUSDC": PaperMarketQuote(
            symbol="ETHUSDC",
            best_bid=Decimal("3200.00"),
            best_ask=Decimal("3200.05"),
            bid_size=Decimal("90"),
            ask_size=Decimal("84"),
            mark_price=Decimal("3200.025"),
            funding_rate_bps=Decimal("0.6"),
            short_horizon_volatility_bps=Decimal("15"),
            freshness=_freshness(reference_time),
        ),
    }


def _metadata_for(account_state: AccountState, symbol: str) -> SymbolMetadata | None:
    for metadata in account_state.symbol_metadata:
        if metadata.symbol == symbol:
            return metadata
    return None


def _fee_for(account_state: AccountState, symbol: str) -> FeePolicy | None:
    for policy in account_state.fee_policies:
        if policy.symbol == symbol:
            return policy
    return None


def _is_multiple(value: Decimal, step: Decimal) -> bool:
    if step <= 0:
        return False
    return value % step == 0


def _would_cross(intent: PaperOrderIntent, quote: PaperMarketQuote) -> bool:
    if intent.side == OrderSide.BUY:
        return intent.limit_price >= quote.best_ask
    return intent.limit_price <= quote.best_bid


def _queue_fill_probability(intent: PaperOrderIntent, quote: PaperMarketQuote) -> Decimal:
    if intent.side == OrderSide.BUY:
        if intent.limit_price > quote.best_bid:
            base = Decimal("0.78")
        elif intent.limit_price == quote.best_bid:
            base = Decimal("0.58")
        else:
            base = Decimal("0.32")
        imbalance_bonus = (quote.ask_size - quote.bid_size) / (
            quote.bid_size + quote.ask_size
        )
    else:
        if intent.limit_price < quote.best_ask:
            base = Decimal("0.78")
        elif intent.limit_price == quote.best_ask:
            base = Decimal("0.58")
        else:
            base = Decimal("0.32")
        imbalance_bonus = (quote.bid_size - quote.ask_size) / (
            quote.bid_size + quote.ask_size
        )
    probability = base + imbalance_bonus * Decimal("0.15")
    return min(Decimal("0.95"), max(Decimal("0.05"), probability))


def calculate_expected_edge(
    intent: PaperOrderIntent,
    fee_policy: FeePolicy,
    quote: PaperMarketQuote,
) -> ExpectedEdgeBreakdown:
    notional = intent.notional
    gross_edge = notional * intent.expected_alpha_bps / Decimal("10000")
    maker_fee = notional * fee_policy.maker_fee_rate
    taker_fee = notional * fee_policy.taker_fee_rate if intent.allow_taker else Decimal("0")
    slippage_cost = notional * intent.slippage_bps / Decimal("10000")
    funding_cost = notional * abs(quote.funding_rate_bps) / Decimal("10000")
    adverse_selection_cost = (
        notional * intent.adverse_selection_bps / Decimal("10000")
    )
    expected_edge_after_costs = (
        gross_edge
        - maker_fee
        - taker_fee
        - slippage_cost
        - funding_cost
        - adverse_selection_cost
    )
    return ExpectedEdgeBreakdown(
        notional=notional,
        gross_edge=gross_edge,
        maker_fee=maker_fee,
        taker_fee=taker_fee,
        slippage_cost=slippage_cost,
        funding_cost=funding_cost,
        adverse_selection_cost=adverse_selection_cost,
        expected_edge_after_costs=expected_edge_after_costs,
    )


class InMemoryPaperExchange:
    def __init__(
        self,
        account_state: AccountState | None = None,
        *,
        taker_gate_enabled: bool = False,
        state_store: PaperExchangeStateStore | None = None,
    ) -> None:
        self._account_state = account_state or default_account_state()
        self._orders: list[PaperOrder] = []
        self._reconciliation_events: list[ReconciliationEvent] = []
        self._taker_gate_enabled = taker_gate_enabled
        self._risk_state = PaperRiskState()
        self._state_store = state_store
        self._halted = False

    def account_state(self) -> AccountState:
        return self._account_state

    def orders(self) -> tuple[PaperOrder, ...]:
        return tuple(self._orders)

    def reconciliation_events(self) -> tuple[ReconciliationEvent, ...]:
        return tuple(self._reconciliation_events)

    def reset(self) -> None:
        self._account_state = default_account_state()
        self._orders.clear()
        self._reconciliation_events.clear()
        self._halted = False
        self._persist_state()

    def panic_halt(self) -> dict[str, object]:
        self._halted = True
        self._risk_state = PaperRiskState(panic_halt_active=True)
        payload = {
            "status": "ok",
            "service": "paper_exchange",
            "panic_halt": True,
            "execution": "paper_only",
        }
        self._persist_state()
        return payload

    def panic_cancel_open_orders(self) -> dict[str, object]:
        canceled_count = 0
        updated_orders: list[PaperOrder] = []
        now = now_utc()
        for order in self._orders:
            if order.status in {OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED}:
                canceled_count += 1
                updated_orders.append(
                    replace(order, status=OrderStatus.CANCELED, updated_at=now)
                )
            else:
                updated_orders.append(order)
        self._orders = updated_orders
        event = ReconciliationEvent(
            event_id=f"paper-recon-{len(self._reconciliation_events) + 1:06d}",
            order_id="all-open-paper-orders",
            status=ReconciliationStatus.CANCELED,
            reason="paper panic cancel recorded",
            created_at=now,
        )
        self._reconciliation_events.append(event)
        self._persist_state()
        return {
            "status": "ok",
            "service": "paper_exchange",
            "execution": "paper_only",
            "open_orders_canceled": canceled_count,
            "reconciliation_event": event.to_public_dict(),
        }

    def panic_flatten_positions(self) -> dict[str, object]:
        self._account_state = default_account_state()
        event = ReconciliationEvent(
            event_id=f"paper-recon-{len(self._reconciliation_events) + 1:06d}",
            order_id="all-paper-positions",
            status=ReconciliationStatus.MATCHED,
            reason="paper positions flattened by resetting local hedge books",
            created_at=now_utc(),
        )
        self._reconciliation_events.append(event)
        self._persist_state()
        return {
            "status": "ok",
            "service": "paper_exchange",
            "execution": "paper_only",
            "flattened": True,
            "portfolio": self.portfolio_payload(),
            "reconciliation_event": event.to_public_dict(),
        }

    def quote_for_symbol(
        self,
        symbol: str,
        reference_time: datetime | None = None,
    ) -> PaperMarketQuote | None:
        now = reference_time or datetime.now(UTC)
        return _default_quotes(now).get(symbol)

    def preview_order(
        self,
        intent: PaperOrderIntent,
        *,
        reference_time: datetime | None = None,
    ) -> PaperOrderPreview:
        now = reference_time or datetime.now(UTC)
        reasons: list[str] = []
        metadata = _metadata_for(self._account_state, intent.symbol)
        fee_policy = _fee_for(self._account_state, intent.symbol)
        quote = self.quote_for_symbol(intent.symbol, now)

        if self._halted:
            reasons.append("paper exchange is halted")
        if metadata is None:
            reasons.append(f"{intent.symbol} metadata is unavailable")
        elif metadata.role != InstrumentRole.EXECUTABLE:
            reasons.append(f"{intent.symbol} is not executable")
        elif metadata.filters is None:
            reasons.append(f"{intent.symbol} executable filters are unavailable")
        else:
            reasons.extend(metadata.validation_errors(now))
            filters = metadata.filters
            if intent.quantity <= 0:
                reasons.append("quantity must be positive")
            if intent.limit_price <= 0:
                reasons.append("limit_price must be positive")
            if not _is_multiple(intent.quantity, filters.lot_size):
                reasons.append("quantity does not align to lot size")
            if not _is_multiple(intent.limit_price, filters.tick_size):
                reasons.append("limit_price does not align to tick size")
            if intent.notional < filters.min_notional:
                reasons.append("order notional is below min notional")

        if fee_policy is None:
            reasons.append(f"{intent.symbol} fee policy is unavailable")
            fee_policy = FeePolicy(
                symbol=intent.symbol,
                maker_fee_rate=Decimal("1"),
                taker_fee_rate=Decimal("1"),
                source="missing_fee_policy",
                freshness=_freshness(now),
            )
        else:
            reasons.extend(fee_policy.validation_errors(now))

        if quote is None:
            reasons.append(f"{intent.symbol} market quote is unavailable")
            quote = PaperMarketQuote(
                symbol=intent.symbol,
                best_bid=Decimal("0"),
                best_ask=Decimal("0"),
                bid_size=Decimal("0"),
                ask_size=Decimal("0"),
                mark_price=Decimal("0"),
                funding_rate_bps=Decimal("0"),
                short_horizon_volatility_bps=Decimal("0"),
                freshness=_freshness(now),
            )
        else:
            reasons.extend(quote.freshness.validation_errors(now, f"{intent.symbol} quote"))

        if intent.order_type.value != "LIMIT":
            reasons.append("paper exchange only supports limit order intents")
        execution_check = validate_maker_first_intent(
            intent,
            quote,
            taker_gate_enabled=self._taker_gate_enabled,
        )
        reasons.extend(execution_check.reasons)

        expected_edge = calculate_expected_edge(intent, fee_policy, quote)
        if expected_edge.expected_edge_after_costs <= 0:
            reasons.append("expected_edge_after_costs must be positive")

        return PaperOrderPreview(
            intent=intent,
            accepted=not reasons,
            reasons=tuple(reasons),
            maker_first=True,
            post_only_would_cross=execution_check.post_only_would_cross,
            expected_edge=expected_edge,
        )

    def submit_order(
        self,
        intent: PaperOrderIntent,
        *,
        reference_time: datetime | None = None,
    ) -> PaperSubmitResult:
        now = reference_time or now_utc()
        preview = self.preview_order(intent, reference_time=now)
        order_id = f"paper-order-{len(self._orders) + 1:06d}"
        if not preview.accepted:
            event = ReconciliationEvent(
                event_id=f"paper-recon-{len(self._reconciliation_events) + 1:06d}",
                order_id=order_id,
                status=ReconciliationStatus.REJECTED,
                reason="; ".join(preview.reasons),
                created_at=now,
            )
            self._reconciliation_events.append(event)
            self._persist_state()
            return PaperSubmitResult(False, preview, None, event)

        quote = self.quote_for_symbol(intent.symbol, now)
        if quote is None:
            raise RuntimeError("accepted preview cannot have missing quote")
        risk_result = evaluate_paper_order_risk(
            self._account_state,
            intent,
            preview,
            quote,
            state=self._risk_state,
            reference_time=now,
        )
        if not risk_result.accepted:
            event = ReconciliationEvent(
                event_id=f"paper-recon-{len(self._reconciliation_events) + 1:06d}",
                order_id=order_id,
                status=ReconciliationStatus.REJECTED,
                reason="; ".join(risk_result.reasons),
                created_at=now,
            )
            self._reconciliation_events.append(event)
            self._persist_state()
            return PaperSubmitResult(False, preview, None, event, risk_result)

        order = PaperOrder(
            order_id=order_id,
            intent=intent,
            status=OrderStatus.NEW,
            created_at=now,
            updated_at=now,
        )
        self._orders.append(order)
        event = ReconciliationEvent(
            event_id=f"paper-recon-{len(self._reconciliation_events) + 1:06d}",
            order_id=order_id,
            status=ReconciliationStatus.RESTING,
            reason="deterministic paper order accepted onto local book",
            created_at=now,
        )
        self._reconciliation_events.append(event)
        self._persist_state()
        return PaperSubmitResult(True, preview, order, event, risk_result)

    def process_open_orders(
        self,
        *,
        reference_time: datetime | None = None,
    ) -> dict[str, object]:
        now = reference_time or now_utc()
        processed: list[dict[str, object]] = []
        for order in tuple(self._orders):
            if order.status not in {OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED}:
                continue
            quote = self.quote_for_symbol(order.intent.symbol, now)
            if quote is None:
                continue
            probability = _queue_fill_probability(order.intent, quote)
            if probability >= Decimal("0.60") or order.status == OrderStatus.PARTIALLY_FILLED:
                updated = self._fill_order(order, order.remaining_quantity, now)
            elif probability >= Decimal("0.25"):
                updated = self._fill_order(
                    order,
                    min(order.remaining_quantity, order.intent.quantity / Decimal("2")),
                    now,
                )
            else:
                updated = replace(order, updated_at=now)
            processed.append(
                {
                    "order_id": updated.order_id,
                    "status": updated.status.value,
                    "filled_quantity": decimal_str(updated.filled_quantity),
                    "remaining_quantity": decimal_str(updated.remaining_quantity),
                    "queue_fill_probability": decimal_str(probability),
                }
            )
        self._persist_state()
        return {
            "status": "ok",
            "service": "paper_exchange",
            "execution": "paper_only",
            "processed": processed,
        }

    def expire_order(self, order_id: str) -> dict[str, object]:
        now = now_utc()
        for index, order in enumerate(self._orders):
            if order.order_id != order_id:
                continue
            if order.status not in {OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED}:
                return {
                    "status": "ok",
                    "service": "paper_exchange",
                    "order_id": order_id,
                    "expired": False,
                    "reason": "only open paper orders can expire",
                }
            expired = replace(order, status=OrderStatus.EXPIRED, updated_at=now)
            self._orders[index] = expired
            event = ReconciliationEvent(
                event_id=f"paper-recon-{len(self._reconciliation_events) + 1:06d}",
                order_id=order_id,
                status=ReconciliationStatus.EXPIRED,
                reason="paper order expired by deterministic lifecycle",
                created_at=now,
            )
            self._reconciliation_events.append(event)
            self._persist_state()
            return {
                "status": "ok",
                "service": "paper_exchange",
                "order_id": order_id,
                "expired": True,
                "reconciliation_event": event.to_public_dict(),
            }
        return {
            "status": "not_found",
            "service": "paper_exchange",
            "order_id": order_id,
        }

    def cancel_order(self, order_id: str) -> dict[str, object]:
        for order in self._orders:
            if order.order_id == order_id:
                if order.status in {OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED}:
                    updated = replace(
                        order,
                        status=OrderStatus.CANCELED,
                        updated_at=now_utc(),
                    )
                    self._orders = [
                        updated if item.order_id == order_id else item
                        for item in self._orders
                    ]
                event = ReconciliationEvent(
                    event_id=f"paper-recon-{len(self._reconciliation_events) + 1:06d}",
                    order_id=order_id,
                    status=ReconciliationStatus.CANCELED,
                    reason="paper cancel request recorded",
                    created_at=now_utc(),
                )
                self._reconciliation_events.append(event)
                self._persist_state()
                return {
                    "status": "ok",
                    "service": "paper_exchange",
                    "order_id": order_id,
                    "canceled": order.status in {
                        OrderStatus.NEW,
                        OrderStatus.PARTIALLY_FILLED,
                    },
                    "reason": (
                        "paper order canceled"
                        if order.status
                        in {OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED}
                        else "terminal paper orders cannot be canceled"
                    ),
                    "reconciliation_event": event.to_public_dict(),
                }
        return {
            "status": "not_found",
            "service": "paper_exchange",
            "order_id": order_id,
        }

    def orders_payload(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "paper_exchange",
            "orders": [order.to_public_dict() for order in self._orders],
        }

    def portfolio_payload(self) -> dict[str, object]:
        payload = portfolio_payload(self._account_state)
        payload["execution"] = "paper_only"
        return payload

    def reconciliation_payload(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "paper_exchange",
            "reconciliation_events": [
                event.to_public_dict() for event in self._reconciliation_events
            ],
        }

    def summary_payload(self, reference_time: datetime | None = None) -> dict[str, Any]:
        now = reference_time or datetime.now(UTC)
        return {
            "status": "ok",
            "service": "paper_exchange",
            "phase": "paper_trading_control_loop",
            "execution": "paper_only",
            "taker_gate_enabled": self._taker_gate_enabled,
            "panic_halted": self._halted,
            "orders_count": len(self._orders),
            "reconciliation_count": len(self._reconciliation_events),
            "portfolio": self.portfolio_payload(),
            "quotes": [
                quote.to_public_dict(now)
                for quote in _default_quotes(now).values()
            ],
            "notes": [
                "local deterministic paper simulator",
                "no Binance connectivity",
                "maker-first by default",
                f"fees use {decimal_str(self._account_state.fee_policies[0].maker_fee_rate)} maker baseline",
            ],
        }

    def _persist_state(self) -> None:
        if not self._state_store:
            return
        self._state_store.persist_orders(self.orders_payload())
        self._state_store.persist_reconciliation(self.reconciliation_payload())
        self._state_store.persist_portfolio(self.portfolio_payload())
        self._state_store.persist_snapshot(self.summary_payload())

    def _fill_order(
        self,
        order: PaperOrder,
        fill_quantity: Decimal,
        created_at: datetime,
    ) -> PaperOrder:
        quantity = min(order.remaining_quantity, fill_quantity)
        if quantity <= 0:
            return order
        fee_policy = _fee_for(self._account_state, order.intent.symbol)
        fee_rate = fee_policy.maker_fee_rate if fee_policy else Decimal("0")
        fill = PaperFill(
            fill_id=f"paper-fill-{sum(len(item.fills) for item in self._orders) + 1:06d}",
            order_id=order.order_id,
            symbol=order.intent.symbol,
            side=order.intent.side,
            book_side=order.intent.book_side,
            quantity=quantity,
            price=order.intent.limit_price,
            liquidity="maker",
            fee=quantity * order.intent.limit_price * fee_rate,
            created_at=created_at,
        )
        filled_quantity = order.filled_quantity + quantity
        status = (
            OrderStatus.FILLED
            if filled_quantity >= order.intent.quantity
            else OrderStatus.PARTIALLY_FILLED
        )
        updated = replace(
            order,
            status=status,
            updated_at=created_at,
            fill=fill,
            fills=(*order.fills, fill),
            filled_quantity=filled_quantity,
        )
        self._orders = [
            updated if item.order_id == order.order_id else item
            for item in self._orders
        ]
        self._account_state = apply_paper_fill(self._account_state, fill)
        event_status = (
            ReconciliationStatus.MATCHED
            if status == OrderStatus.FILLED
            else ReconciliationStatus.PARTIALLY_FILLED
        )
        event = ReconciliationEvent(
            event_id=f"paper-recon-{len(self._reconciliation_events) + 1:06d}",
            order_id=order.order_id,
            status=event_status,
            reason="deterministic maker queue fill applied",
            created_at=created_at,
        )
        self._reconciliation_events.append(event)
        return updated


def default_paper_exchange() -> InMemoryPaperExchange:
    return InMemoryPaperExchange(state_store=PaperExchangeStateStore())
