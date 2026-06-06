"""Local model-governance store and recommendation gates."""

from __future__ import annotations

from typing import Any, Mapping

from libs.schemas import (
    EvaluationResult,
    FeatureVersion,
    ModelDecisionRecord,
    ModelRecommendationPreview,
    RegisteredModel,
    default_evaluation_results,
    default_feature_versions,
    default_model_decision_records,
    default_registered_models,
)
from services.storage import JsonStateStore


class ModelGovernanceStore:
    """Local, public-only model governance state.

    The store persists metadata and decision records, never model binaries,
    training data, exchange credentials, or order-submission artifacts.
    """

    def __init__(
        self,
        *,
        models: tuple[RegisteredModel, ...] | None = None,
        features: tuple[FeatureVersion, ...] | None = None,
        evaluations: tuple[EvaluationResult, ...] | None = None,
        decisions: tuple[ModelDecisionRecord, ...] | None = None,
        store: JsonStateStore | None = None,
    ) -> None:
        self._models = list(models or default_registered_models())
        self._features = list(features or default_feature_versions())
        self._evaluations = list(evaluations or default_evaluation_results())
        self._decisions = list(decisions or default_model_decision_records())
        self._store = store
        self.persist()

    def models(self) -> tuple[RegisteredModel, ...]:
        return tuple(self._models)

    def features(self) -> tuple[FeatureVersion, ...]:
        return tuple(self._features)

    def evaluations(self) -> tuple[EvaluationResult, ...]:
        return tuple(self._evaluations)

    def decisions(self) -> tuple[ModelDecisionRecord, ...]:
        return tuple(self._decisions)

    def add_decision(self, decision: ModelDecisionRecord) -> None:
        errors = decision.validation_errors()
        if errors:
            raise ValueError("; ".join(errors))
        self._decisions.append(decision)
        self.persist()

    def decision_for_recommendation(
        self,
        recommendation_id: str,
    ) -> ModelDecisionRecord | None:
        for decision in reversed(self._decisions):
            if decision.recommendation_id == recommendation_id:
                return decision
        return None

    def recommendation_preview(
        self,
        recommendation_id: str,
    ) -> ModelRecommendationPreview:
        decision = self.decision_for_recommendation(recommendation_id)
        reasons: list[str] = []
        if decision is None:
            reasons.append(
                "model recommendation cannot become an order intent without "
                "a ModelDecisionRecord"
            )
        else:
            reasons.extend(decision.validation_errors())
        return ModelRecommendationPreview(
            recommendation_id=recommendation_id,
            decision_record=decision,
            accepted=not reasons,
            reasons=tuple(reasons),
        )

    def persist(self) -> None:
        if not self._store:
            return
        self._store.write_json("models/registry.json", self.registry_payload())
        self._store.write_json("models/features.json", self.features_payload())
        self._store.write_json("models/evaluations.json", self.evaluations_payload())
        self._store.write_json("models/decisions.json", self.decisions_payload())

    def registry_payload(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "model_service",
            "models": [item.to_public_dict() for item in self._models],
            "notes": [
                "local governance metadata only",
                "model approval cannot bypass risk or live gates",
            ],
        }

    def features_payload(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "model_service",
            "feature_versions": [item.to_public_dict() for item in self._features],
        }

    def evaluations_payload(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "model_service",
            "evaluations": [item.to_public_dict() for item in self._evaluations],
        }

    def decisions_payload(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "model_service",
            "decisions": [item.to_public_dict() for item in self._decisions],
        }


def default_model_governance_store(
    store: JsonStateStore | None = None,
) -> ModelGovernanceStore:
    return ModelGovernanceStore(store=store or JsonStateStore())


_MODEL_STORE = default_model_governance_store()


def model_registry_payload(
    store: ModelGovernanceStore | None = None,
) -> dict[str, object]:
    return (store or _MODEL_STORE).registry_payload()


def feature_registry_payload(
    store: ModelGovernanceStore | None = None,
) -> dict[str, object]:
    return (store or _MODEL_STORE).features_payload()


def evaluation_results_payload(
    store: ModelGovernanceStore | None = None,
) -> dict[str, object]:
    return (store or _MODEL_STORE).evaluations_payload()


def model_decision_records_payload(
    store: ModelGovernanceStore | None = None,
) -> dict[str, object]:
    return (store or _MODEL_STORE).decisions_payload()


def recommendation_preview_payload(
    body: Mapping[str, Any] | None = None,
    *,
    store: ModelGovernanceStore | None = None,
) -> dict[str, object]:
    payload = body or {}
    recommendation_id = str(payload.get("recommendation_id", "strategy-rec-000001"))
    preview = (store or _MODEL_STORE).recommendation_preview(recommendation_id)
    return {
        "status": "ok",
        "service": "model_service",
        "preview": preview.to_public_dict(),
    }
