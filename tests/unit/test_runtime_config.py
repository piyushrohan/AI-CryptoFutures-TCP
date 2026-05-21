import unittest

from libs.config import (
    AutonomyStage,
    ConfigError,
    CredentialScope,
    OperatorMode,
    RuntimeConfig,
    TradingGate,
    VenueTarget,
    load_runtime_config,
)


class RuntimeConfigTests(unittest.TestCase):
    def test_defaults_are_safe_and_need_no_binance_credentials(self):
        config = load_runtime_config({})

        self.assertEqual(config.operator_mode, OperatorMode.PAPER)
        self.assertEqual(config.venue_target, VenueTarget.INTERNAL_PAPER)
        self.assertEqual(config.credential_scope, CredentialScope.NONE)
        self.assertEqual(config.trading_gate, TradingGate.LOCKED)
        self.assertEqual(config.autonomy_stage, AutonomyStage.OBSERVE_ONLY)
        self.assertFalse(config.live_trading_enabled)
        self.assertFalse(config.trading_allowed)
        self.assertTrue(config.fail_closed)
        self.assertFalse(config.binance_credentials_required)
        self.assertFalse(config.binance_credentials_present)
        self.assertEqual(config.validation_errors(), [])

    def test_live_trading_enabled_without_full_gate_fails_closed(self):
        config = load_runtime_config({"LIVE_TRADING_ENABLED": "true"})

        self.assertFalse(config.trading_allowed)
        self.assertTrue(config.fail_closed)
        self.assertIn(
            "live trading enabled without the full live trading gate tuple",
            config.validation_errors(),
        )

    def test_live_trading_requires_explicit_live_tuple(self):
        config = load_runtime_config(
            {
                "OPERATOR_MODE": "live",
                "VENUE_TARGET": "binance_live",
                "CREDENTIAL_SCOPE": "trading",
                "TRADING_GATE": "tiny_live",
                "LIVE_TRADING_ENABLED": "true",
            }
        )

        self.assertTrue(config.trading_allowed)
        self.assertFalse(config.fail_closed)
        self.assertEqual(config.validation_errors(), [])

    def test_live_read_only_cannot_trade(self):
        config = load_runtime_config(
            {
                "OPERATOR_MODE": "live",
                "VENUE_TARGET": "binance_live",
                "CREDENTIAL_SCOPE": "read_only",
                "TRADING_GATE": "locked",
            }
        )

        self.assertFalse(config.live_trading_enabled)
        self.assertFalse(config.trading_allowed)
        self.assertTrue(config.fail_closed)

    def test_invalid_enum_value_is_rejected(self):
        with self.assertRaises(ConfigError):
            load_runtime_config({"OPERATOR_MODE": "testnet"})

    def test_status_never_exposes_secret_values(self):
        config = load_runtime_config(
            {
                "BINANCE_API_KEY": "not-a-real-key",
                "BINANCE_API_SECRET": "not-a-real-secret",
            }
        )

        status = config.to_status()
        self.assertTrue(status["binance_credentials_present"])
        self.assertNotIn("BINANCE_API_KEY", status)
        self.assertNotIn("BINANCE_API_SECRET", status)
        self.assertNotIn("not-a-real-key", str(status))
        self.assertNotIn("not-a-real-secret", str(status))


if __name__ == "__main__":
    unittest.main()
