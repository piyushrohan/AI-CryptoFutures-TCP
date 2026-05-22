"""Execution-policy validation for paper workflows."""

from __future__ import annotations

from dataclasses import dataclass

from libs.schemas import OrderSide, PaperMarketQuote, PaperOrderIntent, TimeInForce


@dataclass(frozen=True)
class ExecutionCheckResult:
    accepted: bool
    reasons: tuple[str, ...]
    post_only_would_cross: bool
    maker_first: bool = True

    def to_public_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "reasons": list(self.reasons),
            "post_only_would_cross": self.post_only_would_cross,
            "maker_first": self.maker_first,
        }


def _would_cross(intent: PaperOrderIntent, quote: PaperMarketQuote) -> bool:
    if intent.side == OrderSide.BUY:
        return intent.limit_price >= quote.best_ask
    return intent.limit_price <= quote.best_bid


def validate_maker_first_intent(
    intent: PaperOrderIntent,
    quote: PaperMarketQuote,
    *,
    taker_gate_enabled: bool = False,
) -> ExecutionCheckResult:
    reasons: list[str] = []
    if intent.time_in_force != TimeInForce.GTX:
        reasons.append("maker-first paper orders must use GTX time-in-force")
    if not intent.post_only:
        reasons.append("maker-first paper orders must be post_only")
    if intent.allow_taker and not taker_gate_enabled:
        reasons.append("taker behavior is not enabled for paper exchange")
    post_only_would_cross = _would_cross(intent, quote)
    if intent.post_only and post_only_would_cross:
        reasons.append("post-only order would cross the paper book")
    return ExecutionCheckResult(
        accepted=not reasons,
        reasons=tuple(reasons),
        post_only_would_cross=post_only_would_cross,
    )
