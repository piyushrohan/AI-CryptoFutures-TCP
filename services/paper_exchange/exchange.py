"""Deterministic in-memory paper exchange.

This service simulates local paper order handling only. It does not connect to
Binance, sign requests, submit venue orders, or model production-grade matching.
"""

from __future__ import annotations

from dataclasses import dataclass
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


PAPER_SOURCE = "local_paper_simulator"


@dataclass(frozen=True)
class PaperSubmitResult:
    accepted: bool
    preview: PaperOrderPreview
    order: PaperOrder | None
    reconciliation_event: ReconciliationEvent

    def to_public_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "preview": self.preview.to_public_dict(),
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
    ) -> None:
        self._account_state = account_state or default_account_state()
        self._orders: list[PaperOrder] = []
        self._reconciliation_events: list[ReconciliationEvent] = []
        self._taker_gate_enabled = taker_gate_enabled
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

    def panic_halt(self) -> dict[str, object]:
        self._halted = True
        return {
            "status": "ok",
            "service": "paper_exchange",
            "panic_halt": True,
            "execution": "paper_only",
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
        if intent.time_in_force != TimeInForce.GTX:
            reasons.append("maker-first paper orders must use GTX time-in-force")
        if not intent.post_only:
            reasons.append("maker-first paper orders must be post_only")
        if intent.allow_taker and not self._taker_gate_enabled:
            reasons.append("taker behavior is not enabled for paper exchange")

        post_only_would_cross = _would_cross(intent, quote)
        if intent.post_only and post_only_would_cross:
            reasons.append("post-only order would cross the paper book")

        expected_edge = calculate_expected_edge(intent, fee_policy, quote)
        if expected_edge.expected_edge_after_costs <= 0:
            reasons.append("expected_edge_after_costs must be positive")

        return PaperOrderPreview(
            intent=intent,
            accepted=not reasons,
            reasons=tuple(reasons),
            maker_first=True,
            post_only_would_cross=post_only_would_cross,
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
            return PaperSubmitResult(False, preview, None, event)

        fill_fee = preview.expected_edge.maker_fee
        fill = PaperFill(
            fill_id=f"paper-fill-{len(self._orders) + 1:06d}",
            order_id=order_id,
            symbol=intent.symbol,
            side=intent.side,
            book_side=intent.book_side,
            quantity=intent.quantity,
            price=intent.limit_price,
            liquidity="maker",
            fee=fill_fee,
            created_at=now,
        )
        order = PaperOrder(
            order_id=order_id,
            intent=intent,
            status=OrderStatus.FILLED,
            created_at=now,
            updated_at=now,
            fill=fill,
        )
        self._orders.append(order)
        self._account_state = apply_paper_fill(self._account_state, fill)
        event = ReconciliationEvent(
            event_id=f"paper-recon-{len(self._reconciliation_events) + 1:06d}",
            order_id=order_id,
            status=ReconciliationStatus.MATCHED,
            reason="deterministic paper fill applied",
            created_at=now,
        )
        self._reconciliation_events.append(event)
        return PaperSubmitResult(True, preview, order, event)

    def cancel_order(self, order_id: str) -> dict[str, object]:
        for order in self._orders:
            if order.order_id == order_id:
                event = ReconciliationEvent(
                    event_id=f"paper-recon-{len(self._reconciliation_events) + 1:06d}",
                    order_id=order_id,
                    status=ReconciliationStatus.CANCELED,
                    reason="paper cancel request recorded",
                    created_at=now_utc(),
                )
                self._reconciliation_events.append(event)
                return {
                    "status": "ok",
                    "service": "paper_exchange",
                    "order_id": order_id,
                    "canceled": order.status != OrderStatus.FILLED,
                    "reason": "filled paper orders cannot be unfilled",
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


def default_paper_exchange() -> InMemoryPaperExchange:
    return InMemoryPaperExchange()
