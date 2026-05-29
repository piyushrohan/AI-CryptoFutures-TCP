"""Model-governance schemas for transparent recommendation review.

These contracts describe model metadata, feature versions, evaluation results,
and decision records. They intentionally stop at governance and explanation;
they do not create an execution path or allow a model to call an exchange.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Mapping

from libs.config import MLOpsApprovalState
from libs.schemas.paper_trading import decimal_from, decimal_str


def _now() -> datetime:
    return datetime.now(UTC)


def _parse_time(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value)
    else:
        raise ValueError(f"{field_name} must be an ISO datetime")
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return parsed


@dataclass(frozen=True)
class FeatureContribution:
    name: str
    value: Decimal
    contribution: Decimal

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "FeatureContribution":
        return cls(
            name=str(payload.get("name", "")),
            value=decimal_from(payload.get("value", "0"), "feature value"),
            contribution=decimal_from(
                payload.get("contribution", "0"),
                "feature contribution",
            ),
        )

    def to_public_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "value": decimal_str(self.value),
            "contribution": decimal_str(self.contribution),
        }


@dataclass(frozen=True)
class FeatureVersion:
    feature_version_id: str
    name: str
    version: str
    input_window: str
    features: tuple[str, ...]
    created_at: datetime
    source: str = "local_microstructure_fixture"

    def to_public_dict(self) -> dict[str, object]:
        return {
            "feature_version_id": self.feature_version_id,
            "name": self.name,
            "version": self.version,
            "input_window": self.input_window,
            "features": list(self.features),
            "source": self.source,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class RegisteredModel:
    model_id: str
    name: str
    version: str
    family: str
    approval_state: MLOpsApprovalState
    feature_version_id: str
    candidate_symbols: tuple[str, ...]
    disabled: bool
    created_at: datetime
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_public_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "version": self.version,
            "family": self.family,
            "approval_state": self.approval_state.value,
            "feature_version_id": self.feature_version_id,
            "candidate_symbols": list(self.candidate_symbols),
            "disabled": self.disabled,
            "created_at": self.created_at.isoformat(),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class EvaluationResult:
    evaluation_id: str
    model_id: str
    model_version: str
    feature_version_id: str
    input_window: str
    backtest_run_id: str
    expected_edge_after_costs: Decimal
    maker_taker_ratio: Decimal
    max_drawdown_bps: Decimal
    approval_state: MLOpsApprovalState
    created_at: datetime

    def to_public_dict(self) -> dict[str, object]:
        return {
            "evaluation_id": self.evaluation_id,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "feature_version_id": self.feature_version_id,
            "input_window": self.input_window,
            "backtest_run_id": self.backtest_run_id,
            "expected_edge_after_costs": decimal_str(
                self.expected_edge_after_costs
            ),
            "maker_taker_ratio": decimal_str(self.maker_taker_ratio),
            "max_drawdown_bps": decimal_str(self.max_drawdown_bps),
            "approval_state": self.approval_state.value,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class ModelDecisionRecord:
    decision_id: str
    recommendation_id: str
    model_id: str
    model_version: str
    feature_version_id: str
    input_window_start: datetime
    input_window_end: datetime
    symbol: str
    prediction: str
    confidence: Decimal
    expected_edge_after_costs: Decimal
    top_features: tuple[FeatureContribution, ...]
    risk_context: Mapping[str, Any]
    rejected_alternatives: tuple[str, ...]
    final_explanation: str
    created_at: datetime

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ModelDecisionRecord":
        features = payload.get("top_features", ())
        if not isinstance(features, list | tuple):
            raise ValueError("top_features must be a list")
        risk_context = payload.get("risk_context", {})
        if not isinstance(risk_context, Mapping):
            raise ValueError("risk_context must be an object")
        rejected_alternatives = payload.get("rejected_alternatives", ())
        if not isinstance(rejected_alternatives, list | tuple):
            raise ValueError("rejected_alternatives must be a list")
        return cls(
            decision_id=str(payload.get("decision_id", "")),
            recommendation_id=str(payload.get("recommendation_id", "")),
            model_id=str(payload.get("model_id", "")),
            model_version=str(payload.get("model_version", "")),
            feature_version_id=str(payload.get("feature_version_id", "")),
            input_window_start=_parse_time(
                payload.get("input_window_start"),
                "input_window_start",
            ),
            input_window_end=_parse_time(
                payload.get("input_window_end"),
                "input_window_end",
            ),
            symbol=str(payload.get("symbol", "")),
            prediction=str(payload.get("prediction", "")),
            confidence=decimal_from(payload.get("confidence", "0"), "confidence"),
            expected_edge_after_costs=decimal_from(
                payload.get("expected_edge_after_costs", "0"),
                "expected_edge_after_costs",
            ),
            top_features=tuple(
                FeatureContribution.from_mapping(item) for item in features
            ),
            risk_context=dict(risk_context),
            rejected_alternatives=tuple(str(item) for item in rejected_alternatives),
            final_explanation=str(payload.get("final_explanation", "")),
            created_at=_parse_time(payload.get("created_at"), "created_at"),
        )

    def validation_errors(self) -> list[str]:
        errors: list[str] = []
        required = {
            "decision_id": self.decision_id,
            "recommendation_id": self.recommendation_id,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "feature_version_id": self.feature_version_id,
            "symbol": self.symbol,
            "prediction": self.prediction,
            "final_explanation": self.final_explanation,
        }
        for field_name, value in required.items():
            if not value:
                errors.append(f"{field_name} is required")
        if self.input_window_end <= self.input_window_start:
            errors.append("input window must have positive duration")
        if not Decimal("0") <= self.confidence <= Decimal("1"):
            errors.append("confidence must be between 0 and 1")
        if self.expected_edge_after_costs <= 0:
            errors.append("expected_edge_after_costs must be positive")
        if not self.top_features:
            errors.append("top_features are required for explainability")
        if not self.risk_context:
            errors.append("risk_context is required")
        return errors

    def to_public_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "recommendation_id": self.recommendation_id,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "feature_version_id": self.feature_version_id,
            "input_window_start": self.input_window_start.isoformat(),
            "input_window_end": self.input_window_end.isoformat(),
            "symbol": self.symbol,
            "prediction": self.prediction,
            "confidence": decimal_str(self.confidence),
            "expected_edge_after_costs": decimal_str(
                self.expected_edge_after_costs
            ),
            "top_features": [item.to_public_dict() for item in self.top_features],
            "risk_context": dict(self.risk_context),
            "rejected_alternatives": list(self.rejected_alternatives),
            "final_explanation": self.final_explanation,
            "created_at": self.created_at.isoformat(),
            "execution": "not_performed",
        }


@dataclass(frozen=True)
class ModelRecommendationPreview:
    recommendation_id: str
    decision_record: ModelDecisionRecord | None
    accepted: bool
    reasons: tuple[str, ...]

    def to_public_dict(self) -> dict[str, object]:
        return {
            "recommendation_id": self.recommendation_id,
            "accepted": self.accepted,
            "reasons": list(self.reasons),
            "decision_record": (
                self.decision_record.to_public_dict()
                if self.decision_record
                else None
            ),
            "execution": "not_performed",
        }


def default_feature_versions(
    reference_time: datetime | None = None,
) -> tuple[FeatureVersion, ...]:
    now = reference_time or _now()
    return (
        FeatureVersion(
            feature_version_id="microstructure-v1",
            name="maker_microstructure_features",
            version="1.0.0",
            input_window="90s",
            features=(
                "order_book_imbalance",
                "microprice",
                "spread_bps",
                "depth_slope",
                "trade_aggression",
                "latency_adjusted_return_bps",
            ),
            created_at=now,
        ),
    )


def default_registered_models(
    reference_time: datetime | None = None,
) -> tuple[RegisteredModel, ...]:
    now = reference_time or _now()
    return (
        RegisteredModel(
            model_id="maker-microstructure-baseline",
            name="Maker Microstructure Baseline",
            version="0.1.0",
            family="deterministic_baseline",
            approval_state=MLOpsApprovalState.RESEARCH_CANDIDATE,
            feature_version_id="microstructure-v1",
            candidate_symbols=("BTCUSDC", "ETHUSDC"),
            disabled=False,
            created_at=now,
            notes=(
                "local governance seed",
                "not approved for testnet or live trading",
                "model output cannot call exchange connectors",
            ),
        ),
    )


def default_evaluation_results(
    reference_time: datetime | None = None,
) -> tuple[EvaluationResult, ...]:
    now = reference_time or _now()
    return (
        EvaluationResult(
            evaluation_id="eval-maker-microstructure-001",
            model_id="maker-microstructure-baseline",
            model_version="0.1.0",
            feature_version_id="microstructure-v1",
            input_window="synthetic_fixture",
            backtest_run_id="synthetic-microstructure-backtest-001",
            expected_edge_after_costs=Decimal("1.52"),
            maker_taker_ratio=Decimal("1"),
            max_drawdown_bps=Decimal("0"),
            approval_state=MLOpsApprovalState.RESEARCH_CANDIDATE,
            created_at=now,
        ),
    )


def default_model_decision_records(
    reference_time: datetime | None = None,
) -> tuple[ModelDecisionRecord, ...]:
    now = reference_time or _now()
    return (
        ModelDecisionRecord(
            decision_id="model-decision-000001",
            recommendation_id="strategy-rec-000001",
            model_id="maker-microstructure-baseline",
            model_version="0.1.0",
            feature_version_id="microstructure-v1",
            input_window_start=now - timedelta(seconds=90),
            input_window_end=now,
            symbol="BTCUSDC",
            prediction="suggest_maker_quote",
            confidence=Decimal("0.62"),
            expected_edge_after_costs=Decimal("1.52"),
            top_features=(
                FeatureContribution(
                    "order_book_imbalance",
                    Decimal("0.18"),
                    Decimal("0.41"),
                ),
                FeatureContribution("microprice", Decimal("65000.3"), Decimal("0.24")),
                FeatureContribution("spread_bps", Decimal("0.08"), Decimal("0.17")),
            ),
            risk_context={
                "operator_mode": "paper",
                "venue_target": "internal_paper",
                "trading_gate": "locked",
                "risk_engine": "independent_veto_required",
            },
            rejected_alternatives=(
                "taker_order_rejected_without_gate",
                "direct_exchange_call_forbidden",
            ),
            final_explanation=(
                "Research candidate suggests a maker-only quote; this is not an "
                "order and still requires command, risk, portfolio, execution, "
                "audit, and reconciliation checks."
            ),
            created_at=now,
        ),
    )
