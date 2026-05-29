import unittest

from apps.api.server import (
    live_order_rejection_payload,
    live_readonly_account_payload,
    recommendation_preview_payload,
    testnet_order_validation_payload,
    testnet_validation_payload,
)
from libs.config import CredentialScope, OperatorMode, RuntimeConfig, TradingGate, VenueTarget
from services.execution import testnet_runtime_fixture
from services.model_service import (
    evaluation_results_payload,
    feature_registry_payload,
    model_decision_records_payload,
    model_registry_payload,
)


ORDER = {
    "symbol": "ETHUSDC",
    "side": "SELL",
    "book_side": "SHORT",
    "quantity": "0.01",
    "limit_price": "3200.00",
}


class PhaseSevenToNineApiTests(unittest.TestCase):
    def test_model_registry_feature_evaluation_and_decision_endpoints(self):
        registry = model_registry_payload()
        features = feature_registry_payload()
        evaluations = evaluation_results_payload()
        decisions = model_decision_records_payload()

        self.assertEqual(registry["status"], "ok")
        self.assertEqual(features["feature_versions"][0]["feature_version_id"], "microstructure-v1")
        self.assertEqual(evaluations["evaluations"][0]["approval_state"], "research_candidate")
        self.assertEqual(decisions["decisions"][0]["execution"], "not_performed")

    def test_recommendation_preview_api_is_not_execution_approval(self):
        payload = recommendation_preview_payload(
            {"recommendation_id": "strategy-rec-000001"}
        )

        self.assertTrue(payload["preview"]["accepted"])
        self.assertEqual(payload["preview"]["execution"], "not_performed")

    def test_testnet_validation_api_stays_locked_without_runtime_gate(self):
        payload = testnet_validation_payload(RuntimeConfig())

        self.assertFalse(payload["accepted"])
        self.assertEqual(payload["network_calls"], "not_performed")

    def test_testnet_order_validation_api_uses_backend_only_payload(self):
        payload = testnet_order_validation_payload(
            ORDER,
            config=testnet_runtime_fixture(),
        )

        self.assertTrue(payload["accepted"])
        self.assertEqual(payload["binance_payload"]["positionSide"], "SHORT")
        self.assertFalse(payload["binance_payload"]["signed_request"])

    def test_live_readonly_api_accepts_only_readonly_live_config(self):
        config = RuntimeConfig(
            operator_mode=OperatorMode.LIVE,
            venue_target=VenueTarget.BINANCE_LIVE,
            credential_scope=CredentialScope.READ_ONLY,
            trading_gate=TradingGate.LOCKED,
            binance_api_key_present=True,
            binance_api_secret_present=True,
        )

        payload = live_readonly_account_payload(config)

        self.assertTrue(payload["accepted"])
        self.assertEqual(payload["snapshot"]["reconciliation"]["order_submission"], "forbidden")
        self.assertTrue(payload["credential_metadata"]["secrets_redacted"])

    def test_live_orders_api_is_explicitly_fail_closed(self):
        payload = live_order_rejection_payload()

        self.assertFalse(payload["accepted"])
        self.assertEqual(payload["order_submission"], "forbidden")


if __name__ == "__main__":
    unittest.main()
