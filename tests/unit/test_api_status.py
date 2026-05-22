import unittest

from apps.api.server import (
    audit_payload,
    health_payload,
    status_payload,
    validate_command_payload,
)
from libs.config import RuntimeConfig
from services.audit import InMemoryAuditRecorder


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

    def test_command_validation_rejects_order_in_observe_only_and_audits(self):
        recorder = InMemoryAuditRecorder()

        payload = validate_command_payload(
            {"command_type": "create_manual_order_intent", "payload": {"symbol": "BTCUSDC"}},
            config=RuntimeConfig(),
            recorder=recorder,
        )

        self.assertEqual(payload["status"], "ok")
        self.assertFalse(payload["command"]["accepted"])
        self.assertEqual(payload["command"]["decision"], "vetoed")
        self.assertEqual(payload["execution"], "not_performed")
        self.assertEqual(len(recorder.records()), 1)

    def test_audit_payload_is_read_only(self):
        recorder = InMemoryAuditRecorder()

        payload = audit_payload(recorder)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["service"], "audit")
        self.assertEqual(payload["records"], [])


if __name__ == "__main__":
    unittest.main()
