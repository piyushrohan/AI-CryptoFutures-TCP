"""Paper-only strategy session manager.

Phase 6 introduces session control and recommendation inspection, not a real
alpha strategy. Recommendations are explainable no-trade records by default and
remain untrusted until later command, risk, portfolio, execution, and audit
workflows approve them.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum

from libs.schemas import FeePolicy, decimal_str, default_fee_policies
from services.backtesting import run_microstructure_backtest
from services.strategy.policies import (
    maker_microstructure_policy,
    microstructure_scalp_policy,
)


class StrategySessionStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    REJECTED = "rejected"


@dataclass(frozen=True)
class StrategyRecommendation:
    recommendation_id: str
    session_id: str
    action: str
    symbol: str
    expected_edge_after_costs: Decimal
    confidence: Decimal
    maker_or_taker_permission: str
    risk_context: str
    explanation: str
    rejected_alternatives: tuple[str, ...]
    created_at: datetime

    def to_public_dict(self) -> dict[str, object]:
        return {
            "recommendation_id": self.recommendation_id,
            "session_id": self.session_id,
            "action": self.action,
            "symbol": self.symbol,
            "expected_edge_after_costs": decimal_str(
                self.expected_edge_after_costs
            ),
            "confidence": decimal_str(self.confidence),
            "maker_or_taker_permission": self.maker_or_taker_permission,
            "risk_context": self.risk_context,
            "explanation": self.explanation,
            "rejected_alternatives": list(self.rejected_alternatives),
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class StrategySession:
    session_id: str
    family: str
    status: StrategySessionStatus
    operator_mode: str
    venue_target: str
    fee_model_source: str
    maker_taker_leakage: Decimal
    started_at: datetime
    updated_at: datetime
    notes: tuple[str, ...]

    def to_public_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "family": self.family,
            "status": self.status.value,
            "operator_mode": self.operator_mode,
            "venue_target": self.venue_target,
            "fee_model_source": self.fee_model_source,
            "maker_taker_leakage": decimal_str(self.maker_taker_leakage),
            "started_at": self.started_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "notes": list(self.notes),
        }


def _fee_model_available(fee_policies: tuple[FeePolicy, ...]) -> tuple[bool, str]:
    now = datetime.now(UTC)
    if not fee_policies:
        return False, "fee model is unavailable"
    errors: list[str] = []
    for policy in fee_policies:
        errors.extend(policy.validation_errors(now))
    if errors:
        return False, "; ".join(errors)
    return True, fee_policies[0].source


class StrategySessionManager:
    def __init__(self, fee_policies: tuple[FeePolicy, ...] | None = None) -> None:
        self._fee_policies = fee_policies or default_fee_policies()
        self._sessions: list[StrategySession] = []
        self._recommendations: list[StrategyRecommendation] = []
        self._audit_records: list[dict[str, object]] = []

    def start_session(self, family: str = "maker_microstructure") -> StrategySession:
        now = datetime.now(UTC)
        fee_available, source_or_reason = _fee_model_available(self._fee_policies)
        session = StrategySession(
            session_id=f"paper-strategy-{len(self._sessions) + 1:06d}",
            family=family,
            status=(
                StrategySessionStatus.RUNNING
                if fee_available
                else StrategySessionStatus.REJECTED
            ),
            operator_mode="paper",
            venue_target="internal_paper",
            fee_model_source=source_or_reason,
            maker_taker_leakage=Decimal("0"),
            started_at=now,
            updated_at=now,
            notes=(
                "paper-only strategy session",
                "maker-first policy",
                "no exchange connector access",
                "strategy alpha is not implemented",
            ),
        )
        self._sessions.append(session)
        self._record_audit(session.session_id, "start", session.status.value)
        if fee_available:
            self._recommendations.append(self._policy_recommendation(session, now))
        return session

    def pause_latest(self) -> StrategySession | None:
        session = self._update_latest(StrategySessionStatus.PAUSED)
        if session:
            self._record_audit(session.session_id, "pause", session.status.value)
        return session

    def stop_latest(self) -> StrategySession | None:
        session = self._update_latest(StrategySessionStatus.STOPPED)
        if session:
            self._record_audit(session.session_id, "stop", session.status.value)
        return session

    def sessions(self) -> tuple[StrategySession, ...]:
        return tuple(self._sessions)

    def recommendations(self) -> tuple[StrategyRecommendation, ...]:
        if not self._sessions:
            session = self.start_session()
            if session.status == StrategySessionStatus.REJECTED:
                return ()
        return tuple(self._recommendations)

    def sessions_payload(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "strategy_sessions",
            "sessions": [item.to_public_dict() for item in self._sessions],
            "recommendations": [
                item.to_public_dict() for item in self._recommendations
            ],
            "audit_records": list(self._audit_records),
        }

    def recommendations_payload(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "strategy_recommendations",
            "recommendations": [
                item.to_public_dict() for item in self.recommendations()
            ],
        }

    def _update_latest(
        self,
        status: StrategySessionStatus,
    ) -> StrategySession | None:
        if not self._sessions:
            return None
        updated = replace(
            self._sessions[-1],
            status=status,
            updated_at=datetime.now(UTC),
        )
        self._sessions[-1] = updated
        return updated

    def _policy_recommendation(
        self,
        session: StrategySession,
        created_at: datetime,
    ) -> StrategyRecommendation:
        report = run_microstructure_backtest()
        policy = (
            microstructure_scalp_policy()
            if session.family == "microstructure_scalp"
            else maker_microstructure_policy(report)
        )
        self._record_audit(session.session_id, "recommendation", policy.action)
        return StrategyRecommendation(
            recommendation_id=f"strategy-rec-{len(self._recommendations) + 1:06d}",
            session_id=session.session_id,
            action=policy.action,
            symbol=policy.symbol,
            expected_edge_after_costs=report.expected_edge_after_costs,
            confidence=policy.confidence,
            maker_or_taker_permission="maker_only",
            risk_context=(
                "paper recommendation only; command, risk, portfolio, execution, "
                "audit, and reconciliation approval still required"
            ),
            explanation=policy.explanation,
            rejected_alternatives=policy.rejected_alternatives,
            created_at=created_at,
        )

    def _record_audit(self, session_id: str, event: str, decision: str) -> None:
        self._audit_records.append(
            {
                "session_id": session_id,
                "event": event,
                "decision": decision,
                "created_at": datetime.now(UTC).isoformat(),
                "scope": "paper_only",
            }
        )


def default_strategy_session_manager() -> StrategySessionManager:
    return StrategySessionManager()
