"""Risk-gate scaffolding for command validation.

This module is deliberately conservative. Phase 1 can approve read-only
inspection commands, but trading-affecting commands and future execution paths
remain blocked until the relevant roadmap phase implements them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from libs.config import (
    AutonomyStage,
    RuntimeConfig,
)
from libs.schemas import (
    CommandEffect,
    CommandRequest,
    command_definition,
)


class RiskDecision(str, Enum):
    APPROVED = "approved"
    VETOED = "vetoed"


@dataclass(frozen=True)
class CommandSafetyResult:
    command_type: str
    accepted: bool
    decision: RiskDecision
    reasons: tuple[str, ...]

    def to_public_dict(self) -> dict[str, object]:
        return {
            "command_type": self.command_type,
            "accepted": self.accepted,
            "decision": self.decision.value,
            "reasons": list(self.reasons),
        }


def _requires_one_of(
    actual: object,
    allowed: tuple[object, ...],
    label: str,
) -> str | None:
    if allowed and actual not in allowed:
        values = ", ".join(item.value for item in allowed)  # type: ignore[attr-defined]
        actual_value = getattr(actual, "value", str(actual))
        return f"{label}={actual_value} is not allowed; expected one of: {values}"
    return None


def evaluate_command(
    config: RuntimeConfig,
    request: CommandRequest,
    *,
    fee_model_available: bool = False,
) -> CommandSafetyResult:
    definition = command_definition(request.command_type)
    reasons: list[str] = []

    reasons.extend(config.validation_errors())
    for possible_reason in (
        _requires_one_of(
            config.operator_mode,
            definition.required_operator_modes,
            "operator_mode",
        ),
        _requires_one_of(
            config.venue_target,
            definition.required_venue_targets,
            "venue_target",
        ),
        _requires_one_of(
            config.credential_scope,
            definition.required_credential_scopes,
            "credential_scope",
        ),
        _requires_one_of(
            config.trading_gate,
            definition.required_trading_gates,
            "trading_gate",
        ),
        _requires_one_of(
            config.autonomy_stage,
            definition.required_autonomy_stages,
            "autonomy_stage",
        ),
        _requires_one_of(
            config.mlops_approval_state,
            definition.required_mlops_states,
            "mlops_approval_state",
        ),
    ):
        if possible_reason:
            reasons.append(possible_reason)

    if definition.trading_affecting and (
        config.autonomy_stage == AutonomyStage.OBSERVE_ONLY
    ):
        reasons.append("observe_only cannot submit or alter trading commands")

    if definition.effect == CommandEffect.LIVE_TRADING and not config.trading_allowed:
        reasons.append("live trading is fail-closed without explicit live gates")

    if definition.requires_fee_model and not fee_model_available:
        reasons.append(
            "fee model is unavailable; expected_edge_after_costs cannot be audited"
        )

    if not definition.execution_available:
        reasons.append("backend execution support is not implemented for this command")

    accepted = not reasons
    return CommandSafetyResult(
        command_type=request.command_type.value,
        accepted=accepted,
        decision=RiskDecision.APPROVED if accepted else RiskDecision.VETOED,
        reasons=tuple(reasons),
    )


def risk_status_payload(config: RuntimeConfig) -> dict[str, object]:
    return {
        "status": "ok",
        "service": "risk",
        "phase": "safety_spine",
        "risk_engine_authority": "veto",
        "trading_allowed": config.trading_allowed,
        "fail_closed": config.fail_closed,
        "live_trading_enabled": config.live_trading_enabled,
        "guardrails": [
            "live trading disabled by default",
            "unsafe config tuples fail closed",
            "observe_only rejects trading-affecting commands",
            "strategy sessions require a current fee model",
            "browser signing is forbidden",
        ],
        "implemented_checks": [
            "runtime tuple validation",
            "command catalog validation",
            "observe_only trading-affecting veto",
            "live trading gate veto",
            "fee model availability veto",
        ],
        "future_checks": [
            "max daily loss",
            "max symbol exposure",
            "portfolio margin and liquidation buffer",
            "stale data kill switch",
            "API error kill switch",
            "abnormal spread kill switch",
            "funding spike kill switch",
            "order spam protection",
        ],
    }
