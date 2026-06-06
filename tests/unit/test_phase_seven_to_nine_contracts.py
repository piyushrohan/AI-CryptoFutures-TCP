from datetime import UTC, datetime, timedelta
from decimal import Decimal
from dataclasses import replace
from tempfile import TemporaryDirectory
import unittest

from libs.binance_connector import (
    BinanceUsdmEnvironment,
    backend_credential_metadata,
    validate_backend_caller,
    validate_usdm_order_payload,
)
from libs.config import CredentialScope, RuntimeConfig, VenueTarget
from libs.schemas import (
    FeatureContribution,
    ModelDecisionRecord,
    PaperOrderIntent,
    InstrumentRole,
    default_account_state,
    default_evaluation_results,
    default_feature_versions,
    default_model_decision_records,
    default_registered_models,
)
from services.execution import testnet_order_validation_payload
from services.model_service import ModelGovernanceStore, recommendation_preview_payload
from services.portfolio import live_order_rejection_payload, live_readonly_account_payload
from services.storage import JsonStateStore


class PhaseSevenToNineContractTests(unittest.TestCase):
    def test_schema_defaults_serialize_public_model_governance_state(self):
        feature = default_feature_versions()[0].to_public_dict()
        model = default_registered_models()[0].to_public_dict()
        evaluation = default_evaluation_results()[0].to_public_dict()
        decision = default_model_decision_records()[0].to_public_dict()

        self.assertEqual(feature["source"], "local_microstructure_fixture")
        self.assertEqual(model["approval_state"], "research_candidate")
        self.assertEqual(evaluation["maker_taker_ratio"], "1")
        self.assertEqual(decision["execution"], "not_performed")

    def test_feature_contribution_from_mapping_is_decimal_safe(self):
        contribution = FeatureContribution.from_mapping(
            {"name": "spread_bps", "value": "0.08", "contribution": "0.17"}
        )

        self.assertEqual(contribution.to_public_dict()["value"], "0.08")

    def test_model_decision_from_mapping_rejects_bad_shapes(self):
        base = default_model_decision_records()[0].to_public_dict()

        with self.assertRaises(ValueError):
            ModelDecisionRecord.from_mapping(dict(base, top_features="bad"))
        with self.assertRaises(ValueError):
            ModelDecisionRecord.from_mapping(dict(base, risk_context="bad"))
        with self.assertRaises(ValueError):
            ModelDecisionRecord.from_mapping(dict(base, rejected_alternatives="bad"))
        with self.assertRaises(ValueError):
            ModelDecisionRecord.from_mapping(dict(base, created_at="2026-01-01T00:00:00"))
        with self.assertRaises(ValueError):
            ModelDecisionRecord.from_mapping(dict(base, created_at=object()))

    def test_model_decision_from_mapping_accepts_datetime_objects(self):
        base = default_model_decision_records()[0].to_public_dict()
        now = datetime.now(UTC)
        base.update(
            {
                "input_window_start": now - timedelta(seconds=90),
                "input_window_end": now,
                "created_at": now,
            }
        )

        parsed = ModelDecisionRecord.from_mapping(base)

        self.assertEqual(parsed.created_at, now)

    def test_model_decision_validation_lists_all_required_explainability_fields(self):
        now = datetime.now(UTC)
        decision = ModelDecisionRecord(
            decision_id="",
            recommendation_id="",
            model_id="",
            model_version="",
            feature_version_id="",
            input_window_start=now,
            input_window_end=now - timedelta(seconds=1),
            symbol="",
            prediction="",
            confidence=Decimal("-0.1"),
            expected_edge_after_costs=Decimal("0"),
            top_features=(),
            risk_context={},
            rejected_alternatives=(),
            final_explanation="",
            created_at=now,
        )

        errors = "; ".join(decision.validation_errors())

        self.assertIn("decision_id is required", errors)
        self.assertIn("input window", errors)
        self.assertIn("confidence", errors)
        self.assertIn("top_features", errors)
        self.assertIn("risk_context", errors)

    def test_model_governance_store_accessors_and_valid_add(self):
        with TemporaryDirectory() as tmp:
            store = ModelGovernanceStore(
                decisions=(),
                store=JsonStateStore(tmp),
            )
            decision = default_model_decision_records()[0]

            store.add_decision(decision)

            self.assertEqual(store.models()[0].model_id, "maker-microstructure-baseline")
            self.assertEqual(store.features()[0].feature_version_id, "microstructure-v1")
            self.assertEqual(store.evaluations()[0].evaluation_id, "eval-maker-microstructure-001")
            self.assertEqual(store.decisions()[0].decision_id, decision.decision_id)
            self.assertEqual(
                store.decision_for_recommendation("strategy-rec-000001"),
                decision,
            )

    def test_recommendation_preview_uses_default_recommendation_id(self):
        payload = recommendation_preview_payload()

        self.assertTrue(payload["preview"]["accepted"])
        self.assertEqual(payload["preview"]["recommendation_id"], "strategy-rec-000001")

    def test_recommendation_preview_without_decision_serializes_none(self):
        preview = ModelGovernanceStore(decisions=()).recommendation_preview("missing")

        payload = preview.to_public_dict()

        self.assertIsNone(payload["decision_record"])

    def test_binance_environment_and_backend_caller_contracts(self):
        validate_backend_caller("backend_api")

        self.assertIn("testnet", BinanceUsdmEnvironment.TESTNET.rest_base_url)
        self.assertEqual(BinanceUsdmEnvironment.LIVE.rest_base_url, "https://fapi.binance.com")

    def test_binance_payload_rejects_wrong_runtime_and_missing_credentials(self):
        metadata = next(
            item for item in default_account_state().symbol_metadata
            if item.symbol == "BTCUSDC"
        )
        payload, reasons = validate_usdm_order_payload(
            PaperOrderIntent.from_mapping(
                {
                    "symbol": "BTCUSDC",
                    "side": "BUY",
                    "book_side": "LONG",
                    "quantity": "0.001",
                    "limit_price": "65000.4",
                }
            ),
            metadata,
            config=RuntimeConfig(),
        )

        self.assertIsNone(payload)
        self.assertIn("Binance venue target", "; ".join(reasons))
        self.assertIn("credentials", "; ".join(reasons))

    def test_binance_payload_rejects_non_executable_symbol_metadata(self):
        metadata = next(
            item for item in default_account_state().symbol_metadata
            if item.symbol == "BTCUSDC"
        )
        non_executable = replace(metadata, role=InstrumentRole.REFERENCE)
        payload, reasons = validate_usdm_order_payload(
            PaperOrderIntent.from_mapping(
                {
                    "symbol": "BTCUSDC",
                    "side": "BUY",
                    "book_side": "LONG",
                    "quantity": "0.001",
                    "limit_price": "65000.4",
                }
            ),
            non_executable,
            config=RuntimeConfig(
                venue_target=VenueTarget.BINANCE_TESTNET,
                credential_scope=CredentialScope.TRADING,
                binance_api_key_present=True,
                binance_api_secret_present=True,
            ),
        )

        self.assertIsNone(payload)
        self.assertIn("symbol is not executable under current symbol policy", reasons)

    def test_binance_payload_reports_filter_and_caller_safety_reasons(self):
        metadata = next(
            item for item in default_account_state().symbol_metadata
            if item.symbol == "BTCUSDC"
        )
        mismatched = replace(metadata, symbol="ETHUSDC")

        payload, reasons = validate_usdm_order_payload(
            PaperOrderIntent.from_mapping(
                {
                    "symbol": "BTCUSDC",
                    "side": "BUY",
                    "book_side": "LONG",
                    "quantity": "0.0003",
                    "limit_price": "65000.4",
                    "time_in_force": "GTC",
                }
            ),
            mismatched,
            config=RuntimeConfig(
                venue_target=VenueTarget.BINANCE_TESTNET,
                credential_scope=CredentialScope.TRADING,
                binance_api_key_present=True,
                binance_api_secret_present=True,
            ),
            caller="frontend",
        )

        joined = "; ".join(reasons)
        self.assertIsNone(payload)
        self.assertIn("browser code must never sign", joined)
        self.assertIn("symbol does not match", joined)
        self.assertIn("GTX", joined)
        self.assertIn("lot size", joined)
        self.assertIn("min notional", joined)

    def test_binance_payload_handles_invalid_filter_step_defensively(self):
        metadata = next(
            item for item in default_account_state().symbol_metadata
            if item.symbol == "BTCUSDC"
        )
        bad_filters = replace(metadata.filters, lot_size=Decimal("0"))
        bad_metadata = replace(metadata, filters=bad_filters)

        payload, reasons = validate_usdm_order_payload(
            PaperOrderIntent.from_mapping(
                {
                    "symbol": "BTCUSDC",
                    "side": "BUY",
                    "book_side": "LONG",
                    "quantity": "0.001",
                    "limit_price": "65000.4",
                }
            ),
            bad_metadata,
            config=RuntimeConfig(
                venue_target=VenueTarget.BINANCE_TESTNET,
                credential_scope=CredentialScope.TRADING,
                binance_api_key_present=True,
                binance_api_secret_present=True,
            ),
        )

        self.assertIsNone(payload)
        self.assertIn("quantity does not align to Binance lot size", reasons)

    def test_binance_payload_rejects_missing_filters(self):
        metadata = next(
            item for item in default_account_state().symbol_metadata
            if item.symbol == "BTCUSDC"
        )
        without_filters = replace(metadata, filters=None)

        payload, reasons = validate_usdm_order_payload(
            PaperOrderIntent.from_mapping(
                {
                    "symbol": "BTCUSDC",
                    "side": "BUY",
                    "book_side": "LONG",
                    "quantity": "0.001",
                    "limit_price": "65000.4",
                }
            ),
            without_filters,
            config=RuntimeConfig(
                venue_target=VenueTarget.BINANCE_TESTNET,
                credential_scope=CredentialScope.TRADING,
                binance_api_key_present=True,
                binance_api_secret_present=True,
            ),
        )

        self.assertIsNone(payload)
        self.assertEqual(reasons, ("symbol filters are unavailable",))

    def test_testnet_order_validation_reports_missing_metadata(self):
        payload = testnet_order_validation_payload(
            {"symbol": "UNKNOWN", "quantity": "1", "limit_price": "1"},
            config=RuntimeConfig(
                venue_target=VenueTarget.BINANCE_TESTNET,
                credential_scope=CredentialScope.TRADING,
                binance_api_key_present=True,
                binance_api_secret_present=True,
            ),
        )

        self.assertFalse(payload["accepted"])
        self.assertIn("metadata is unavailable", payload["translation_reasons"][0])

    def test_live_readonly_rejected_audit_and_redacted_metadata(self):
        config = RuntimeConfig(
            operator_mode=RuntimeConfig().operator_mode.LIVE,
            venue_target=VenueTarget.BINANCE_LIVE,
            credential_scope=CredentialScope.READ_ONLY,
        )
        payload = live_readonly_account_payload(config)
        metadata = backend_credential_metadata(config)

        self.assertFalse(payload["accepted"])
        self.assertIn("read-only Binance credentials", "; ".join(payload["reasons"]))
        self.assertTrue(metadata["secrets_redacted"])

    def test_live_order_rejection_payload_uses_supplied_runtime(self):
        config = RuntimeConfig(venue_target=VenueTarget.BINANCE_LIVE)
        payload = live_order_rejection_payload(config)

        self.assertFalse(payload["accepted"])
        self.assertEqual(payload["runtime"]["venue_target"], "binance_live")


if __name__ == "__main__":
    unittest.main()
