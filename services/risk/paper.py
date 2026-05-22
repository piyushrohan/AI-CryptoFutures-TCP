"""Independent paper risk gates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from libs.schemas import (
    AccountState,
    BookSide,
    PaperMarketQuote,
    PaperOrderIntent,
    PaperOrderPreview,
    decimal_str,
)
from services.portfolio import calculate_portfolio_exposure


@dataclass(frozen=True)
class RiskLimits:
    max_account_leverage: Decimal = Decimal("3")
    max_symbol_exposure: Decimal = Decimal("50000")
    max_portfolio_gross_exposure: Decimal = Decimal("100000")
    min_liquidation_distance_ratio: Decimal = Decimal("0.25")
    max_daily_loss: Decimal = Decimal("1000")
    max_drawdown: Decimal = Decimal("1500")
    max_abnormal_spread_bps: Decimal = Decimal("25")
    max_funding_rate_bps: Decimal = Decimal("50")
    max_short_horizon_volatility_bps: Decimal = Decimal("150")
    max_orders_per_minute: int = 10


@dataclass(frozen=True)
class PaperRiskState:
    daily_loss: Decimal = Decimal("0")
    drawdown: Decimal = Decimal("0")
    open_order_count_last_minute: int = 0
    api_error_active: bool = False
    panic_halt_active: bool = False


@dataclass(frozen=True)
class PaperRiskResult:
    accepted: bool
    reasons: tuple[str, ...]
    limits: RiskLimits

    def to_public_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "decision": "approved" if self.accepted else "vetoed",
            "reasons": list(self.reasons),
            "limits": {
                "max_account_leverage": decimal_str(self.limits.max_account_leverage),
                "max_symbol_exposure": decimal_str(self.limits.max_symbol_exposure),
                "max_portfolio_gross_exposure": decimal_str(
                    self.limits.max_portfolio_gross_exposure
                ),
                "min_liquidation_distance_ratio": decimal_str(
                    self.limits.min_liquidation_distance_ratio
                ),
                "max_daily_loss": decimal_str(self.limits.max_daily_loss),
                "max_drawdown": decimal_str(self.limits.max_drawdown),
                "max_abnormal_spread_bps": decimal_str(
                    self.limits.max_abnormal_spread_bps
                ),
                "max_funding_rate_bps": decimal_str(
                    self.limits.max_funding_rate_bps
                ),
                "max_short_horizon_volatility_bps": decimal_str(
                    self.limits.max_short_horizon_volatility_bps
                ),
                "max_orders_per_minute": self.limits.max_orders_per_minute,
            },
        }


def _projected_symbol_exposure(
    account_state: AccountState,
    intent: PaperOrderIntent,
) -> Decimal:
    current = sum(
        book.notional
        for book in account_state.position_books
        if book.symbol == intent.symbol
    )
    return current + intent.notional


def _projected_gross_exposure(
    account_state: AccountState,
    intent: PaperOrderIntent,
) -> Decimal:
    exposure = calculate_portfolio_exposure(account_state)
    return exposure.gross_exposure + intent.notional


def _account_collateral(account_state: AccountState) -> Decimal:
    if not account_state.collateral_assets:
        return Decimal("0")
    return account_state.collateral_assets[0].wallet_balance


def evaluate_paper_order_risk(
    account_state: AccountState,
    intent: PaperOrderIntent,
    preview: PaperOrderPreview,
    quote: PaperMarketQuote,
    *,
    limits: RiskLimits | None = None,
    state: PaperRiskState | None = None,
    reference_time: datetime,
) -> PaperRiskResult:
    selected_limits = limits or RiskLimits()
    selected_state = state or PaperRiskState()
    reasons: list[str] = []

    reasons.extend(account_state.validation_errors(reference_time))
    reasons.extend(quote.freshness.validation_errors(reference_time, f"{intent.symbol} quote"))

    if selected_state.panic_halt_active:
        reasons.append("panic halt is active")
    if selected_state.api_error_active:
        reasons.append("API error kill switch is active")
    if selected_state.daily_loss >= selected_limits.max_daily_loss:
        reasons.append("max daily loss limit reached")
    if selected_state.drawdown >= selected_limits.max_drawdown:
        reasons.append("max drawdown limit reached")
    if (
        selected_state.open_order_count_last_minute
        >= selected_limits.max_orders_per_minute
    ):
        reasons.append("order spam protection limit reached")

    if preview.expected_edge.expected_edge_after_costs <= 0:
        reasons.append("risk veto: expected_edge_after_costs is not positive")
    if quote.spread_bps > selected_limits.max_abnormal_spread_bps:
        reasons.append("abnormal spread kill switch is active")
    if abs(quote.funding_rate_bps) > selected_limits.max_funding_rate_bps:
        reasons.append("funding spike kill switch is active")
    if (
        quote.short_horizon_volatility_bps
        > selected_limits.max_short_horizon_volatility_bps
    ):
        reasons.append("volatility halt is active")
    if (
        account_state.liquidation_distance_ratio
        < selected_limits.min_liquidation_distance_ratio
    ):
        reasons.append("liquidation buffer is below minimum")

    symbol_exposure = _projected_symbol_exposure(account_state, intent)
    if symbol_exposure > selected_limits.max_symbol_exposure:
        reasons.append("max symbol exposure would be exceeded")

    gross_exposure = _projected_gross_exposure(account_state, intent)
    if gross_exposure > selected_limits.max_portfolio_gross_exposure:
        reasons.append("max portfolio gross exposure would be exceeded")

    collateral = _account_collateral(account_state)
    if collateral <= 0:
        reasons.append("collateral is unavailable")
    elif gross_exposure / collateral > selected_limits.max_account_leverage:
        reasons.append("max account leverage would be exceeded")

    hedge_books = {
        (book.symbol, book.side) for book in account_state.position_books
    }
    if (intent.symbol, BookSide.LONG) not in hedge_books:
        reasons.append(f"{intent.symbol} missing hedge LONG book")
    if (intent.symbol, BookSide.SHORT) not in hedge_books:
        reasons.append(f"{intent.symbol} missing hedge SHORT book")

    return PaperRiskResult(
        accepted=not reasons,
        reasons=tuple(reasons),
        limits=selected_limits,
    )
