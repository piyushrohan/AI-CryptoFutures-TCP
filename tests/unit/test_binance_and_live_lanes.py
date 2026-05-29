import unittest

from libs.binance_connector import (
    ConnectorBoundaryError,
    backend_credential_metadata,
    build_usdm_request_specs,
    validate_backend_caller,
    validate_usdm_order_payload,
)
from libs.config import (
    AutonomyStage,
    CredentialScope,
    OperatorMode,
    RuntimeConfig,
    TradingGate,
    VenueTarget,
)
from libs.schemas import PaperOrderIntent, default_account_state
from services.audit import InMemoryAuditRecorder
from services.execution import (
    testnet_order_validation_payload,
    testnet_runtime_fixture,
    testnet_validation_payload,
)
from services.portfolio import live_order_rejection_payload, live_readonly_account_payload


ORDER = {
    "symbol": "BTCUSDC",
    "side": "BUY",
    "book_side": "LONG",
    "quantity": "0.001",
    "limit_price": "65000.4",
    "time_in_force": "GTX",
    "post_only": True,
    "allow_taker": False,
}


class BinanceAndLiveLaneTests(unittest.TestCase):
    def test_connector_boundary_rejects_browser_callers(self):
        with self.assertRaises(ConnectorBoundaryError):
            validate_backend_caller("browser")

    def test_connector_boundary_returns_only_credential_metadata(self):
        config = RuntimeConfig(
            venue_target=VenueTarget.BINANCE_TESTNET,
            credential_scope=CredentialScope.TRADING,
            binance_api_key_present=True,
            binance_api_secret_present=True,
        )

        metadata = backend_credential_metadata(config)

        self.assertTrue(metadata["api_key_present"])
        self.assertTrue(metadata["secrets_redacted"])
        self.assertNotIn("api_key", metadata)
        self.assertNotIn("api_secret", metadata)

    def test_request_specs_include_binance_usdm_validation_surface(self):
        specs = {item.name: item.to_public_dict() for item in build_usdm_request_specs()}

        self.assertIn("exchange_info", specs)
        self.assertIn("new_order", specs)
        self.assertEqual(specs["new_order"]["path"], "/fapi/v1/order")
        self.assertTrue(specs["new_order"]["signed"])

    def test_usdm_order_payload_maps_hedge_book_to_position_side(self):
        account = default_account_state()
        metadata = next(item for item in account.symbol_metadata if item.symbol == "BTCUSDC")
        payload, reasons = validate_usdm_order_payload(
            PaperOrderIntent.from_mapping(ORDER),
            metadata,
            config=testnet_runtime_fixture(),
        )

        self.assertEqual(reasons, ())
        self.assertEqual(payload.to_public_dict()["positionSide"], "LONG")
        self.assertFalse(payload.to_public_dict()["signed_request"])
        self.assertFalse(payload.to_public_dict()["submitted"])

    def test_usdm_order_payload_rejects_taker_and_bad_filter_shape(self):
        account = default_account_state()
        metadata = next(item for item in account.symbol_metadata if item.symbol == "BTCUSDC")
        bad = dict(ORDER, allow_taker=True, post_only=False, limit_price="65000.41")

        payload, reasons = validate_usdm_order_payload(
            PaperOrderIntent.from_mapping(bad),
            metadata,
            config=testnet_runtime_fixture(),
        )

        self.assertIsNone(payload)
        self.assertIn("maker-first", "; ".join(reasons))
        self.assertIn("tick size", "; ".join(reasons))

    def test_testnet_validation_lane_is_locked_by_default(self):
        payload = testnet_validation_payload(RuntimeConfig())

        self.assertFalse(payload["accepted"])
        self.assertEqual(payload["network_calls"], "not_performed")
        self.assertEqual(payload["order_submission"], "not_performed")

    def test_testnet_order_payload_validation_accepts_only_gated_fixture(self):
        payload = testnet_order_validation_payload(
            ORDER,
            config=testnet_runtime_fixture(),
        )

        self.assertTrue(payload["accepted"])
        self.assertEqual(payload["binance_payload"]["positionSide"], "LONG")
        self.assertEqual(payload["order_submission"], "not_performed")

    def test_live_readonly_requires_live_readonly_tuple_and_credentials(self):
        locked = live_readonly_account_payload(RuntimeConfig())

        self.assertFalse(locked["accepted"])
        self.assertIsNone(locked["snapshot"])

        config = RuntimeConfig(
            operator_mode=OperatorMode.LIVE,
            venue_target=VenueTarget.BINANCE_LIVE,
            credential_scope=CredentialScope.READ_ONLY,
            trading_gate=TradingGate.LOCKED,
            binance_api_key_present=True,
            binance_api_secret_present=True,
        )
        recorder = InMemoryAuditRecorder()
        opened = live_readonly_account_payload(config, recorder=recorder)

        self.assertTrue(opened["accepted"])
        self.assertEqual(opened["order_submission"], "forbidden")
        self.assertEqual(opened["snapshot"]["reconciliation"]["status"], "audit_only")
        self.assertEqual(len(recorder.records()), 1)

    def test_live_readonly_does_not_allow_live_trade_tuple_to_submit(self):
        config = RuntimeConfig(
            operator_mode=OperatorMode.LIVE,
            venue_target=VenueTarget.BINANCE_LIVE,
            credential_scope=CredentialScope.TRADING,
            trading_gate=TradingGate.TINY_LIVE,
            autonomy_stage=AutonomyStage.TINY_LIVE_AUTO,
            live_trading_enabled=True,
            binance_api_key_present=True,
            binance_api_secret_present=True,
        )

        payload = live_order_rejection_payload(config)

        self.assertFalse(payload["accepted"])
        self.assertEqual(payload["order_submission"], "forbidden")
        self.assertIn("out of scope", payload["reasons"][0])


if __name__ == "__main__":
    unittest.main()
