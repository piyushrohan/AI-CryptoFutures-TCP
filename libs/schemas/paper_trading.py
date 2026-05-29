"""Paper trading lifecycle schemas.

These types are deterministic local contracts only. They model paper order
intent, cost preview, fills, reconciliation, and portfolio summaries without
creating any Binance connectivity or live-trading path.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping

from libs.schemas.exchange_state import (
    BookSide,
    Freshness,
    OrderSide,
    OrderStatus,
    TimeInForce,
)


class PaperOrderType(str, Enum):
    LIMIT = "LIMIT"


class PaperExecutionPolicy(str, Enum):
    MAKER_FIRST = "maker_first"


class ReconciliationStatus(str, Enum):
    MATCHED = "matched"
    REJECTED = "rejected"
    CANCELED = "canceled"
    RESTING = "resting"
    PARTIALLY_FILLED = "partially_filled"
    EXPIRED = "expired"


def decimal_from(value: object, field_name: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a decimal value") from exc
    return parsed


def decimal_str(value: Decimal) -> str:
    return format(value, "f")


@dataclass(frozen=True)
class PaperMarketQuote:
    symbol: str
    best_bid: Decimal
    best_ask: Decimal
    bid_size: Decimal
    ask_size: Decimal
    mark_price: Decimal
    funding_rate_bps: Decimal
    short_horizon_volatility_bps: Decimal
    freshness: Freshness

    @property
    def mid_price(self) -> Decimal:
        return (self.best_bid + self.best_ask) / Decimal("2")

    @property
    def spread(self) -> Decimal:
        return self.best_ask - self.best_bid

    @property
    def spread_bps(self) -> Decimal:
        if self.mid_price <= 0:
            return Decimal("0")
        return (self.spread / self.mid_price) * Decimal("10000")

    def to_public_dict(self, reference_time: datetime) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "best_bid": decimal_str(self.best_bid),
            "best_ask": decimal_str(self.best_ask),
            "bid_size": decimal_str(self.bid_size),
            "ask_size": decimal_str(self.ask_size),
            "mark_price": decimal_str(self.mark_price),
            "mid_price": decimal_str(self.mid_price),
            "spread": decimal_str(self.spread),
            "spread_bps": decimal_str(self.spread_bps),
            "funding_rate_bps": decimal_str(self.funding_rate_bps),
            "short_horizon_volatility_bps": decimal_str(
                self.short_horizon_volatility_bps
            ),
            "freshness": self.freshness.to_public_dict(reference_time),
        }


@dataclass(frozen=True)
class PaperOrderIntent:
    symbol: str
    side: OrderSide
    book_side: BookSide
    quantity: Decimal
    limit_price: Decimal
    time_in_force: TimeInForce = TimeInForce.GTX
    order_type: PaperOrderType = PaperOrderType.LIMIT
    post_only: bool = True
    reduce_only: bool = False
    allow_taker: bool = False
    expected_alpha_bps: Decimal = Decimal("8")
    slippage_bps: Decimal = Decimal("0.5")
    adverse_selection_bps: Decimal = Decimal("1")
    client_order_id: str = "paper-local-order"

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "PaperOrderIntent":
        symbol = payload.get("symbol", "BTCUSDC")
        if not isinstance(symbol, str) or not symbol:
            raise ValueError("symbol must be a non-empty string")
        side_value = payload.get("side", OrderSide.BUY.value)
        book_side_value = payload.get("book_side", BookSide.LONG.value)
        tif_value = payload.get("time_in_force", TimeInForce.GTX.value)
        return cls(
            symbol=symbol,
            side=OrderSide(str(side_value)),
            book_side=BookSide(str(book_side_value)),
            quantity=decimal_from(payload.get("quantity", "0.001"), "quantity"),
            limit_price=decimal_from(
                payload.get("limit_price", payload.get("price", "0")),
                "limit_price",
            ),
            time_in_force=TimeInForce(str(tif_value)),
            post_only=bool(payload.get("post_only", True)),
            reduce_only=bool(payload.get("reduce_only", False)),
            allow_taker=bool(payload.get("allow_taker", False)),
            expected_alpha_bps=decimal_from(
                payload.get("expected_alpha_bps", "8"),
                "expected_alpha_bps",
            ),
            slippage_bps=decimal_from(
                payload.get("slippage_bps", "0.5"),
                "slippage_bps",
            ),
            adverse_selection_bps=decimal_from(
                payload.get("adverse_selection_bps", "1"),
                "adverse_selection_bps",
            ),
            client_order_id=str(payload.get("client_order_id", "paper-local-order")),
        )

    @property
    def notional(self) -> Decimal:
        return self.quantity * self.limit_price

    def to_public_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "book_side": self.book_side.value,
            "quantity": decimal_str(self.quantity),
            "limit_price": decimal_str(self.limit_price),
            "time_in_force": self.time_in_force.value,
            "order_type": self.order_type.value,
            "post_only": self.post_only,
            "reduce_only": self.reduce_only,
            "allow_taker": self.allow_taker,
            "expected_alpha_bps": decimal_str(self.expected_alpha_bps),
            "slippage_bps": decimal_str(self.slippage_bps),
            "adverse_selection_bps": decimal_str(self.adverse_selection_bps),
            "notional": decimal_str(self.notional),
            "client_order_id": self.client_order_id,
        }


@dataclass(frozen=True)
class ExpectedEdgeBreakdown:
    notional: Decimal
    gross_edge: Decimal
    maker_fee: Decimal
    taker_fee: Decimal
    slippage_cost: Decimal
    funding_cost: Decimal
    adverse_selection_cost: Decimal
    expected_edge_after_costs: Decimal

    def to_public_dict(self) -> dict[str, object]:
        return {
            "notional": decimal_str(self.notional),
            "gross_edge": decimal_str(self.gross_edge),
            "maker_fee": decimal_str(self.maker_fee),
            "taker_fee": decimal_str(self.taker_fee),
            "slippage_cost": decimal_str(self.slippage_cost),
            "funding_cost": decimal_str(self.funding_cost),
            "adverse_selection_cost": decimal_str(self.adverse_selection_cost),
            "expected_edge_after_costs": decimal_str(
                self.expected_edge_after_costs
            ),
        }


@dataclass(frozen=True)
class PaperOrderPreview:
    intent: PaperOrderIntent
    accepted: bool
    reasons: tuple[str, ...]
    maker_first: bool
    post_only_would_cross: bool
    expected_edge: ExpectedEdgeBreakdown

    def to_public_dict(self) -> dict[str, object]:
        return {
            "intent": self.intent.to_public_dict(),
            "accepted": self.accepted,
            "reasons": list(self.reasons),
            "maker_first": self.maker_first,
            "post_only_would_cross": self.post_only_would_cross,
            "expected_edge": self.expected_edge.to_public_dict(),
        }


@dataclass(frozen=True)
class PaperFill:
    fill_id: str
    order_id: str
    symbol: str
    side: OrderSide
    book_side: BookSide
    quantity: Decimal
    price: Decimal
    liquidity: str
    fee: Decimal
    created_at: datetime

    def to_public_dict(self) -> dict[str, object]:
        return {
            "fill_id": self.fill_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "book_side": self.book_side.value,
            "quantity": decimal_str(self.quantity),
            "price": decimal_str(self.price),
            "liquidity": self.liquidity,
            "fee": decimal_str(self.fee),
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class PaperOrder:
    order_id: str
    intent: PaperOrderIntent
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    fill: PaperFill | None = None
    fills: tuple[PaperFill, ...] = ()
    filled_quantity: Decimal = Decimal("0")

    @property
    def remaining_quantity(self) -> Decimal:
        return max(Decimal("0"), self.intent.quantity - self.filled_quantity)

    def to_public_dict(self) -> dict[str, object]:
        return {
            "order_id": self.order_id,
            "intent": self.intent.to_public_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "fill": self.fill.to_public_dict() if self.fill else None,
            "fills": [item.to_public_dict() for item in self.fills],
            "filled_quantity": decimal_str(self.filled_quantity),
            "remaining_quantity": decimal_str(self.remaining_quantity),
        }


@dataclass(frozen=True)
class ReconciliationEvent:
    event_id: str
    order_id: str
    status: ReconciliationStatus
    reason: str
    created_at: datetime

    def to_public_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "order_id": self.order_id,
            "status": self.status.value,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class PortfolioExposure:
    gross_exposure: Decimal
    net_exposure: Decimal
    long_exposure: Decimal
    short_exposure: Decimal
    hedge_ratio: Decimal
    liquidation_buffer: Decimal
    funding_exposure: Decimal
    sector_exposure: Decimal = Decimal("0")
    correlated_exposure: Decimal = Decimal("0")
    beta_exposure: Decimal = Decimal("0")
    leg_imbalance: Decimal = Decimal("0")
    cross_margin_buffer: Decimal = Decimal("0")

    def to_public_dict(self) -> dict[str, object]:
        return {
            "gross_exposure": decimal_str(self.gross_exposure),
            "net_exposure": decimal_str(self.net_exposure),
            "long_exposure": decimal_str(self.long_exposure),
            "short_exposure": decimal_str(self.short_exposure),
            "hedge_ratio": decimal_str(self.hedge_ratio),
            "liquidation_buffer": decimal_str(self.liquidation_buffer),
            "funding_exposure": decimal_str(self.funding_exposure),
            "sector_exposure": decimal_str(self.sector_exposure),
            "correlated_exposure": decimal_str(self.correlated_exposure),
            "beta_exposure": decimal_str(self.beta_exposure),
            "leg_imbalance": decimal_str(self.leg_imbalance),
            "cross_margin_buffer": decimal_str(self.cross_margin_buffer),
        }


def now_utc() -> datetime:
    return datetime.now(UTC)
