import unittest

from apps.api.server import health_payload, status_payload
from libs.config import RuntimeConfig


class ApiStatusTests(unittest.TestCase):
    def test_health_payload_is_minimal(self):
        self.assertEqual(health_payload(), {"status": "ok", "service": "api"})

    def test_status_payload_exposes_safe_runtime_defaults(self):
        payload = status_payload(RuntimeConfig())
        runtime = payload["runtime"]

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(runtime["operator_mode"], "paper")
        self.assertEqual(runtime["venue_target"], "internal_paper")
        self.assertEqual(runtime["credential_scope"], "none")
        self.assertEqual(runtime["trading_gate"], "locked")
        self.assertEqual(runtime["autonomy_stage"], "observe_only")
        self.assertFalse(runtime["live_trading_enabled"])
        self.assertFalse(runtime["trading_allowed"])
        self.assertFalse(runtime["binance_credentials_required"])

    def test_status_payload_includes_bootstrap_placeholders(self):
        placeholders = status_payload(RuntimeConfig())["placeholders"]

        self.assertEqual(placeholders["api"], "running")
        self.assertEqual(placeholders["frontend"], "expected")
        self.assertEqual(placeholders["database"], "expected")
        self.assertEqual(placeholders["redis"], "expected")
        self.assertEqual(placeholders["monitoring"], "expected")


if __name__ == "__main__":
    unittest.main()
