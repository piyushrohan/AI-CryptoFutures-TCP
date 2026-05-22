"""Deterministic exchange and account state schemas for Phase 2.

These models are local truth-model scaffolding only. They do not connect to
Binance, fetch account data, submit orders, or claim that mocked metadata is
exchange truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum

from libs.schemas.symbol_universe import InstrumentRole, symbol_universe


class _StrEnum(str, Enum):
    pass


class MarginMode(_StrEnum):
    ISOLATED = "isolated"
    CROSS = "cross"
    PORTFOLIO_MARGIN = "portfolio_margin"


class PositionMode(_StrEnum):
    ONE_WAY = "one_way"
    HEDGE = "hedge"


class BookSide(_StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class OrderSide(_StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(_StrEnum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class TimeInForce(_StrEnum):
    GTC = "GTC"
    GTX = "GTX"
    IOC = "IOC"
    FOK = "FOK"
    GTD = "GTD"


PHASE2_SOURCE = "local_mock_phase2"
DEFAULT_MAX_AGE_SECONDS = 300


def _decimal(value: str) -> Decimal:
    return Decimal(value)


def _decimal_str(value: Decimal) -> str:
    return format(value, "f")


@dataclass(frozen=True)
class Freshness:
    source: str
    source_timestamp: datetime
    received_timestamp: datetime
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS

    def age_seconds(self, reference_time: datetime) -> float:
        return max(
            0.0,
            (reference_time - self.received_timestamp).total_seconds(),
        )

    def is_stale(self, reference_time: datetime) -> bool:
        return self.age_seconds(reference_time) > self.max_age_seconds

    def validation_errors(
        self,
        reference_time: datetime,
        label: str,
    ) -> list[str]:
        errors: list[str] = []
        if self.source_timestamp.tzinfo is None:
            errors.append(f"{label} source_timestamp must be timezone-aware")
        if self.received_timestamp.tzinfo is None:
            errors.append(f"{label} received_timestamp must be timezone-aware")
        if self.source_timestamp > self.received_timestamp:
            errors.append(f"{label} source_timestamp cannot be after received_timestamp")
        if self.is_stale(reference_time):
            errors.append(f"{label} is stale")
        return errors

    def to_public_dict(self, reference_time: datetime) -> dict[str, object]:
        return {
            "source": self.source,
            "source_timestamp": self.source_timestamp.isoformat(),
            "received_timestamp": self.received_timestamp.isoformat(),
            "max_age_seconds": self.max_age_seconds,
            "age_seconds": round(self.age_seconds(reference_time), 6),
            "is_stale": self.is_stale(reference_time),
        }


@dataclass(frozen=True)
class CollateralAsset:
    asset: str
    wallet_balance: Decimal
    available_balance: Decimal
    unrealized_pnl: Decimal = Decimal("0")

    def to_public_dict(self) -> dict[str, str]:
        return {
            "asset": self.asset,
            "wallet_balance": _decimal_str(self.wallet_balance),
            "available_balance": _decimal_str(self.available_balance),
            "unrealized_pnl": _decimal_str(self.unrealized_pnl),
        }


@dataclass(frozen=True)
class PositionBook:
    symbol: str
    side: BookSide
    quantity: Decimal
    entry_price: Decimal
    mark_price: Decimal
    notional: Decimal
    unrealized_pnl: Decimal

    def to_public_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": _decimal_str(self.quantity),
            "entry_price": _decimal_str(self.entry_price),
            "mark_price": _decimal_str(self.mark_price),
            "notional": _decimal_str(self.notional),
            "unrealized_pnl": _decimal_str(self.unrealized_pnl),
        }


@dataclass(frozen=True)
class OpenOrder:
    order_id: str
    symbol: str
    side: OrderSide
    book_side: BookSide | None
    quantity: Decimal
    price: Decimal
    status: OrderStatus
    reduce_only: bool
    post_only: bool

    def to_public_dict(self) -> dict[str, object]:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "book_side": self.book_side.value if self.book_side else None,
            "quantity": _decimal_str(self.quantity),
            "price": _decimal_str(self.price),
            "status": self.status.value,
            "reduce_only": self.reduce_only,
            "post_only": self.post_only,
        }


@dataclass(frozen=True)
class SymbolFilters:
    tick_size: Decimal
    lot_size: Decimal
    min_quantity: Decimal
    max_quantity: Decimal
    min_notional: Decimal
    supported_order_types: tuple[str, ...]
    supported_time_in_force: tuple[TimeInForce, ...]

    def validation_errors(self, symbol: str) -> list[str]:
        errors: list[str] = []
        if self.tick_size <= 0:
            errors.append(f"{symbol} tick_size must be positive")
        if self.lot_size <= 0:
            errors.append(f"{symbol} lot_size must be positive")
        if self.min_quantity <= 0:
            errors.append(f"{symbol} min_quantity must be positive")
        if self.max_quantity < self.min_quantity:
            errors.append(f"{symbol} max_quantity cannot be below min_quantity")
        if self.min_notional <= 0:
            errors.append(f"{symbol} min_notional must be positive")
        if "LIMIT" not in self.supported_order_types:
            errors.append(f"{symbol} must support LIMIT orders for maker-first policy")
        if TimeInForce.GTX not in self.supported_time_in_force:
            errors.append(f"{symbol} must support GTX for post-only research")
        return errors

    def to_public_dict(self) -> dict[str, object]:
        return {
            "tick_size": _decimal_str(self.tick_size),
            "lot_size": _decimal_str(self.lot_size),
            "min_quantity": _decimal_str(self.min_quantity),
            "max_quantity": _decimal_str(self.max_quantity),
            "min_notional": _decimal_str(self.min_notional),
            "supported_order_types": list(self.supported_order_types),
            "supported_time_in_force": [
                item.value for item in self.supported_time_in_force
            ],
        }


@dataclass(frozen=True)
class SymbolMetadata:
    symbol: str
    role: InstrumentRole
    venue_symbol: str | None
    contract_status: str
    quote_asset: str | None
    margin_asset: str | None
    filters: SymbolFilters | None
    freshness: Freshness
    metadata_source: str

    def is_executable(self) -> bool:
        return self.role == InstrumentRole.EXECUTABLE

    def validation_errors(self, reference_time: datetime) -> list[str]:
        errors = self.freshness.validation_errors(reference_time, self.symbol)
        if self.is_executable():
            if self.contract_status != "TRADING":
                errors.append(f"{self.symbol} contract_status must be TRADING")
            if self.quote_asset != "USDC":
                errors.append(f"{self.symbol} executable instruments must quote USDC")
            if self.margin_asset != "USDC":
                errors.append(f"{self.symbol} executable instruments must margin in USDC")
            if self.filters is None:
                errors.append(f"{self.symbol} executable instruments require filters")
            else:
                errors.extend(self.filters.validation_errors(self.symbol))
        elif self.filters is not None:
            errors.append(f"{self.symbol} non-executable instruments must not carry executable filters")
        return errors

    def to_public_dict(self, reference_time: datetime) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "role": self.role.value,
            "venue_symbol": self.venue_symbol,
            "contract_status": self.contract_status,
            "quote_asset": self.quote_asset,
            "margin_asset": self.margin_asset,
            "metadata_source": self.metadata_source,
            "is_executable": self.is_executable(),
            "filters": self.filters.to_public_dict() if self.filters else None,
            "freshness": self.freshness.to_public_dict(reference_time),
        }


@dataclass(frozen=True)
class FeePromotion:
    source: str
    effective_from: datetime
    effective_until: datetime
    review_at: datetime
    approval_reference: str
    fallback_maker_fee_rate: Decimal

    def validation_errors(self, reference_time: datetime, symbol: str) -> list[str]:
        errors: list[str] = []
        if self.effective_until <= self.effective_from:
            errors.append(f"{symbol} fee promotion must have an end time")
        if self.review_at > self.effective_until:
            errors.append(f"{symbol} fee promotion review_at must not exceed effective_until")
        if not self.approval_reference:
            errors.append(f"{symbol} fee promotion requires approval_reference")
        if self.fallback_maker_fee_rate < 0:
            errors.append(f"{symbol} fallback maker fee cannot be negative")
        if reference_time > self.effective_until:
            errors.append(f"{symbol} fee promotion is expired")
        return errors

    def to_public_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "effective_from": self.effective_from.isoformat(),
            "effective_until": self.effective_until.isoformat(),
            "review_at": self.review_at.isoformat(),
            "approval_reference": self.approval_reference,
            "fallback_maker_fee_rate": _decimal_str(self.fallback_maker_fee_rate),
        }


@dataclass(frozen=True)
class FeePolicy:
    symbol: str
    maker_fee_rate: Decimal
    taker_fee_rate: Decimal
    source: str
    freshness: Freshness
    promotion: FeePromotion | None = None

    def validation_errors(self, reference_time: datetime) -> list[str]:
        errors = self.freshness.validation_errors(reference_time, f"{self.symbol} fee policy")
        if self.maker_fee_rate < 0:
            errors.append(f"{self.symbol} maker fee cannot be negative")
        if self.taker_fee_rate < 0:
            errors.append(f"{self.symbol} taker fee cannot be negative")
        if self.maker_fee_rate == 0 and self.promotion is None:
            errors.append(
                f"{self.symbol} zero maker fee requires time-bounded promotion metadata"
            )
        if self.promotion:
            errors.extend(self.promotion.validation_errors(reference_time, self.symbol))
        return errors

    def to_public_dict(self, reference_time: datetime) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "maker_fee_rate": _decimal_str(self.maker_fee_rate),
            "taker_fee_rate": _decimal_str(self.taker_fee_rate),
            "source": self.source,
            "promotion": self.promotion.to_public_dict() if self.promotion else None,
            "freshness": self.freshness.to_public_dict(reference_time),
        }


@dataclass(frozen=True)
class AccountState:
    account_id: str
    venue_target: str
    margin_mode: MarginMode
    position_mode: PositionMode
    portfolio_margin_enabled: bool
    collateral_assets: tuple[CollateralAsset, ...]
    maintenance_margin: Decimal
    liquidation_distance_ratio: Decimal
    unrealized_pnl: Decimal
    funding_exposure: Decimal
    open_orders: tuple[OpenOrder, ...]
    position_books: tuple[PositionBook, ...]
    symbol_metadata: tuple[SymbolMetadata, ...]
    fee_policies: tuple[FeePolicy, ...]
    freshness: Freshness

    def validation_errors(self, reference_time: datetime) -> list[str]:
        errors = self.freshness.validation_errors(reference_time, "account state")
        if self.portfolio_margin_enabled:
            errors.append("Portfolio Margin is research-only in Phase 2")
        if self.maintenance_margin < 0:
            errors.append("maintenance_margin cannot be negative")
        if self.liquidation_distance_ratio < 0:
            errors.append("liquidation_distance_ratio cannot be negative")

        for metadata in self.symbol_metadata:
            errors.extend(metadata.validation_errors(reference_time))
        for policy in self.fee_policies:
            errors.extend(policy.validation_errors(reference_time))

        if self.position_mode == PositionMode.HEDGE:
            executable = {
                item.symbol for item in self.symbol_metadata if item.is_executable()
            }
            books = {(book.symbol, book.side) for book in self.position_books}
            for symbol in executable:
                if (symbol, BookSide.LONG) not in books:
                    errors.append(f"{symbol} missing hedge LONG book")
                if (symbol, BookSide.SHORT) not in books:
                    errors.append(f"{symbol} missing hedge SHORT book")
        return errors

    def to_public_dict(self, reference_time: datetime) -> dict[str, object]:
        errors = self.validation_errors(reference_time)
        return {
            "account_id": self.account_id,
            "venue_target": self.venue_target,
            "margin_mode": self.margin_mode.value,
            "position_mode": self.position_mode.value,
            "portfolio_margin_enabled": self.portfolio_margin_enabled,
            "collateral_assets": [
                item.to_public_dict() for item in self.collateral_assets
            ],
            "maintenance_margin": _decimal_str(self.maintenance_margin),
            "liquidation_distance_ratio": _decimal_str(
                self.liquidation_distance_ratio
            ),
            "unrealized_pnl": _decimal_str(self.unrealized_pnl),
            "funding_exposure": _decimal_str(self.funding_exposure),
            "open_orders": [item.to_public_dict() for item in self.open_orders],
            "position_books": [item.to_public_dict() for item in self.position_books],
            "symbol_metadata": [
                item.to_public_dict(reference_time) for item in self.symbol_metadata
            ],
            "fee_policies": [
                item.to_public_dict(reference_time) for item in self.fee_policies
            ],
            "freshness": self.freshness.to_public_dict(reference_time),
            "validation_errors": errors,
            "is_valid": not errors,
        }


def _freshness(reference_time: datetime, source: str = PHASE2_SOURCE) -> Freshness:
    return Freshness(
        source=source,
        source_timestamp=reference_time,
        received_timestamp=reference_time,
    )


def _filters(symbol: str) -> SymbolFilters:
    if symbol == "BTCUSDC":
        return SymbolFilters(
            tick_size=_decimal("0.1"),
            lot_size=_decimal("0.001"),
            min_quantity=_decimal("0.001"),
            max_quantity=_decimal("1000"),
            min_notional=_decimal("50"),
            supported_order_types=("LIMIT",),
            supported_time_in_force=(TimeInForce.GTC, TimeInForce.GTX),
        )
    if symbol == "ETHUSDC":
        return SymbolFilters(
            tick_size=_decimal("0.01"),
            lot_size=_decimal("0.001"),
            min_quantity=_decimal("0.001"),
            max_quantity=_decimal("10000"),
            min_notional=_decimal("20"),
            supported_order_types=("LIMIT",),
            supported_time_in_force=(TimeInForce.GTC, TimeInForce.GTX),
        )
    raise ValueError(f"no Phase 2 executable filters for {symbol}")


def default_symbol_metadata(reference_time: datetime | None = None) -> tuple[SymbolMetadata, ...]:
    now = reference_time or datetime.now(UTC)
    metadata: list[SymbolMetadata] = []
    for instrument in symbol_universe():
        executable = instrument.role == InstrumentRole.EXECUTABLE
        metadata.append(
            SymbolMetadata(
                symbol=instrument.symbol,
                role=instrument.role,
                venue_symbol=instrument.venue_symbol,
                contract_status="TRADING" if executable else "NOT_EXECUTABLE",
                quote_asset="USDC" if executable else None,
                margin_asset="USDC" if executable else None,
                filters=_filters(instrument.symbol) if executable else None,
                freshness=_freshness(now),
                metadata_source="local_mock_not_exchange_truth",
            )
        )
    return tuple(metadata)


def default_fee_policies(reference_time: datetime | None = None) -> tuple[FeePolicy, ...]:
    now = reference_time or datetime.now(UTC)
    return (
        FeePolicy(
            symbol="BTCUSDC",
            maker_fee_rate=_decimal("0.000100"),
            taker_fee_rate=_decimal("0.000400"),
            source="local_configurable_phase2_assumption",
            freshness=_freshness(now),
        ),
        FeePolicy(
            symbol="ETHUSDC",
            maker_fee_rate=_decimal("0.000100"),
            taker_fee_rate=_decimal("0.000400"),
            source="local_configurable_phase2_assumption",
            freshness=_freshness(now),
        ),
    )


def default_position_books() -> tuple[PositionBook, ...]:
    books: list[PositionBook] = []
    for symbol in ("BTCUSDC", "ETHUSDC"):
        for side in (BookSide.LONG, BookSide.SHORT):
            books.append(
                PositionBook(
                    symbol=symbol,
                    side=side,
                    quantity=Decimal("0"),
                    entry_price=Decimal("0"),
                    mark_price=Decimal("0"),
                    notional=Decimal("0"),
                    unrealized_pnl=Decimal("0"),
                )
            )
    return tuple(books)


def default_account_state(reference_time: datetime | None = None) -> AccountState:
    now = reference_time or datetime.now(UTC)
    return AccountState(
        account_id="local-paper-account",
        venue_target="internal_paper",
        margin_mode=MarginMode.CROSS,
        position_mode=PositionMode.HEDGE,
        portfolio_margin_enabled=False,
        collateral_assets=(
            CollateralAsset(
                asset="USDC",
                wallet_balance=Decimal("100000"),
                available_balance=Decimal("100000"),
            ),
        ),
        maintenance_margin=Decimal("0"),
        liquidation_distance_ratio=Decimal("1"),
        unrealized_pnl=Decimal("0"),
        funding_exposure=Decimal("0"),
        open_orders=(),
        position_books=default_position_books(),
        symbol_metadata=default_symbol_metadata(now),
        fee_policies=default_fee_policies(now),
        freshness=_freshness(now),
    )


def stale_freshness(
    reference_time: datetime,
    *,
    seconds_old: int = DEFAULT_MAX_AGE_SECONDS + 1,
) -> Freshness:
    timestamp = reference_time - timedelta(seconds=seconds_old)
    return Freshness(
        source=PHASE2_SOURCE,
        source_timestamp=timestamp,
        received_timestamp=timestamp,
    )
