import unittest

from libs.config import AutonomyStage, RuntimeConfig
from libs.schemas import CommandRequest, CommandType
from services.audit import InMemoryAuditRecorder
from services.risk import RiskDecision, evaluate_command


class CommandSafetySpineTests(unittest.TestCase):
    def test_observe_only_rejects_manual_order_intent(self):
        result = evaluate_command(
            RuntimeConfig(),
            CommandRequest(CommandType.CREATE_MANUAL_ORDER_INTENT),
        )

        self.assertFalse(result.accepted)
        self.assertEqual(result.decision, RiskDecision.VETOED)
        self.assertIn(
            "observe_only cannot submit or alter trading commands",
            result.reasons,
        )

    def test_strategy_session_rejected_without_fee_model(self):
        result = evaluate_command(
            RuntimeConfig(autonomy_stage=AutonomyStage.PAPER_AUTO),
            CommandRequest(CommandType.CREATE_STRATEGY_SESSION),
        )

        self.assertFalse(result.accepted)
        self.assertIn(
            "fee model is unavailable; expected_edge_after_costs cannot be audited",
            result.reasons,
        )

    def test_read_only_status_command_is_approved(self):
        result = evaluate_command(
            RuntimeConfig(),
            CommandRequest(CommandType.GET_SYSTEM_STATUS),
        )

        self.assertTrue(result.accepted)
        self.assertEqual(result.decision, RiskDecision.APPROVED)
        self.assertEqual(result.reasons, ())

    def test_live_order_approval_fails_closed_without_live_tuple(self):
        result = evaluate_command(
            RuntimeConfig(),
            CommandRequest(CommandType.APPROVE_LIVE_ORDER_INTENT),
        )

        self.assertFalse(result.accepted)
        self.assertIn(
            "live trading is fail-closed without explicit live gates",
            result.reasons,
        )

    def test_audit_record_excludes_payload_values(self):
        recorder = InMemoryAuditRecorder()
        payload = {"BINANCE_API_SECRET": "do-not-store-this", "symbol": "BTCUSDC"}

        record = recorder.record_decision(
            command_type="create_manual_order_intent",
            actor_id="tester",
            decision="rejected",
            reasons=["test"],
            payload=payload,
            runtime=RuntimeConfig().to_status(),
        )

        public_record = str(record.to_public_dict())
        self.assertIn("BINANCE_API_SECRET", public_record)
        self.assertIn("symbol", public_record)
        self.assertNotIn("do-not-store-this", public_record)
        self.assertNotIn("BTCUSDC", public_record)


if __name__ == "__main__":
    unittest.main()
