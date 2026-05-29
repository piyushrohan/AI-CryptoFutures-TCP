from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from libs.schemas import (
    FeatureContribution,
    ModelDecisionRecord,
    default_model_decision_records,
)
from services.model_service import (
    ModelGovernanceStore,
    model_decision_records_payload,
    recommendation_preview_payload,
)
from services.storage import JsonStateStore


class ModelGovernanceTests(unittest.TestCase):
    def test_default_model_decision_record_is_complete_and_explainable(self):
        decision = default_model_decision_records()[0]

        self.assertEqual(decision.validation_errors(), [])
        payload = decision.to_public_dict()
        self.assertEqual(payload["execution"], "not_performed")
        self.assertIn("expected_edge_after_costs", payload)
        self.assertGreater(len(payload["top_features"]), 0)
        self.assertIn("risk_engine", payload["risk_context"])

    def test_recommendation_preview_rejects_missing_decision_record(self):
        store = ModelGovernanceStore(decisions=())

        preview = store.recommendation_preview("missing-rec")

        self.assertFalse(preview.accepted)
        self.assertIsNone(preview.decision_record)
        self.assertIn("ModelDecisionRecord", preview.reasons[0])

    def test_recommendation_preview_accepts_complete_decision_record(self):
        store = ModelGovernanceStore()

        payload = recommendation_preview_payload(
            {"recommendation_id": "strategy-rec-000001"},
            store=store,
        )

        self.assertTrue(payload["preview"]["accepted"])
        self.assertEqual(
            payload["preview"]["decision_record"]["decision_id"],
            "model-decision-000001",
        )

    def test_invalid_decision_record_cannot_be_added(self):
        now = datetime.now(UTC)
        decision = ModelDecisionRecord(
            decision_id="bad-decision",
            recommendation_id="bad-rec",
            model_id="model",
            model_version="0.1.0",
            feature_version_id="features",
            input_window_start=now,
            input_window_end=now - timedelta(seconds=1),
            symbol="BTCUSDC",
            prediction="suggest_maker_quote",
            confidence=Decimal("1.5"),
            expected_edge_after_costs=Decimal("-1"),
            top_features=(),
            risk_context={},
            rejected_alternatives=(),
            final_explanation="bad",
            created_at=now,
        )
        store = ModelGovernanceStore(decisions=())

        with self.assertRaises(ValueError):
            store.add_decision(decision)

    def test_decision_record_from_mapping_validates_shape(self):
        source = default_model_decision_records()[0].to_public_dict()
        source["top_features"] = [
            {"name": "microprice", "value": "65000.3", "contribution": "0.4"}
        ]

        parsed = ModelDecisionRecord.from_mapping(source)

        self.assertEqual(parsed.decision_id, "model-decision-000001")
        self.assertEqual(
            parsed.top_features[0],
            FeatureContribution("microprice", Decimal("65000.3"), Decimal("0.4")),
        )

    def test_model_governance_store_persists_public_payloads(self):
        with TemporaryDirectory() as tmp:
            store = ModelGovernanceStore(store=JsonStateStore(tmp))

            self.assertTrue(Path(tmp, "models", "registry.json").exists())
            self.assertTrue(Path(tmp, "models", "decisions.json").exists())
            self.assertEqual(model_decision_records_payload(store)["status"], "ok")


if __name__ == "__main__":
    unittest.main()
