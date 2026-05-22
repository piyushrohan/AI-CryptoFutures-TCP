"""Deterministic paper-only strategy recommendation policies."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from services.backtesting import BacktestReport
from services.market_data import MicrostructureFeatureRow, generate_microstructure_features


@dataclass(frozen=True)
class PolicyRecommendation:
    action: str
    symbol: str
    confidence: Decimal
    explanation: str
    rejected_alternatives: tuple[str, ...]


def maker_microstructure_policy(report: BacktestReport) -> PolicyRecommendation:
    if report.expected_edge_after_costs <= 0 or report.taker_order_count > 0:
        return PolicyRecommendation(
            action="NO_TRADE",
            symbol="SYN_ETHBTC",
            confidence=Decimal("0"),
            explanation=(
                "No paper quote is suggested because expected edge after costs "
                "is unavailable or maker-only discipline was violated."
            ),
            rejected_alternatives=(
                "market orders remain disabled",
                "direct ETHBTC execution remains disabled",
            ),
        )
    return PolicyRecommendation(
        action="SUGGEST_MAKER_QUOTE",
        symbol="BTCUSDC",
        confidence=Decimal("0.55"),
        explanation=(
            "Paper-only maker quote candidate from deterministic fixture edge; "
            "this is not execution approval."
        ),
        rejected_alternatives=(
            "taker quote rejected by maker-first policy",
            "direct ETHBTC execution remains disabled",
        ),
    )


def microstructure_scalp_policy(
    features: tuple[MicrostructureFeatureRow, ...] | None = None,
) -> PolicyRecommendation:
    rows = features or generate_microstructure_features()
    latest = rows[-1]
    aligned_long = (
        latest.order_book_imbalance > Decimal("0.05")
        and latest.trade_aggression > Decimal("0.05")
    )
    aligned_short = (
        latest.order_book_imbalance < Decimal("-0.05")
        and latest.trade_aggression < Decimal("-0.05")
    )
    if not (aligned_long or aligned_short):
        return PolicyRecommendation(
            action="NO_TRADE",
            symbol=latest.symbol,
            confidence=Decimal("0"),
            explanation=(
                "No scalp recommendation because imbalance and trade aggression "
                "are not aligned."
            ),
            rejected_alternatives=(
                "unconfirmed scalp rejected",
                "taker scalp rejected by maker-first policy",
            ),
        )
    direction = "LONG" if aligned_long else "SHORT"
    return PolicyRecommendation(
        action=f"SUGGEST_MICROSTRUCTURE_SCALP_{direction}",
        symbol=latest.symbol,
        confidence=Decimal("0.60"),
        explanation=(
            "Paper-only scalp candidate from aligned order-book imbalance and "
            "trade aggression; this is not execution approval."
        ),
        rejected_alternatives=(
            "market order rejected by maker-first policy",
            "model-driven order rejected because models are not implemented",
        ),
    )
