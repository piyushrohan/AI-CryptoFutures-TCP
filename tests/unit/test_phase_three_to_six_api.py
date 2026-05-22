import unittest

from apps.api.server import (
    paper_process_payload,
    paper_preview_payload,
    paper_reset_payload,
    paper_submit_payload,
    strategy_pause_payload,
    strategy_start_payload,
    strategy_stop_payload,
)
from libs.config import AutonomyStage, RuntimeConfig
from services.paper_exchange import InMemoryPaperExchange
from services.strategy import StrategySessionManager


ORDER = {
    "symbol": "BTCUSDC",
    "side": "BUY",
    "book_side": "LONG",
    "quantity": "0.001",
    "limit_price": "65000.4",
}


class PhaseThreeToSixApiTests(unittest.TestCase):
    def test_paper_preview_is_available_without_order_submission(self):
        payload = paper_preview_payload(ORDER, exchange=InMemoryPaperExchange())

        self.assertEqual(payload["execution"], "paper_only")
        self.assertTrue(payload["preview"]["accepted"])
        self.assertIn("expected_edge_after_costs", payload["preview"]["expected_edge"])

    def test_paper_submit_default_observe_only_is_rejected(self):
        payload = paper_submit_payload(
            ORDER,
            config=RuntimeConfig(),
            exchange=InMemoryPaperExchange(),
        )

        self.assertEqual(payload["execution"], "not_performed")
        self.assertFalse(payload["command"]["accepted"])
        self.assertIsNone(payload["paper_result"])

    def test_paper_submit_human_approval_is_paper_only(self):
        payload = paper_submit_payload(
            ORDER,
            config=RuntimeConfig(autonomy_stage=AutonomyStage.HUMAN_APPROVAL),
            exchange=InMemoryPaperExchange(),
        )

        self.assertEqual(payload["execution"], "paper_only")
        self.assertTrue(payload["paper_result"]["accepted"])
        self.assertEqual(payload["paper_result"]["order"]["status"], "NEW")

    def test_paper_process_advances_open_orders(self):
        exchange = InMemoryPaperExchange()
        paper_submit_payload(
            ORDER,
            config=RuntimeConfig(autonomy_stage=AutonomyStage.HUMAN_APPROVAL),
            exchange=exchange,
        )

        payload = paper_process_payload({}, exchange=exchange)

        self.assertEqual(payload["execution"], "paper_only")
        self.assertEqual(payload["processed"][0]["status"], "FILLED")

    def test_paper_reset_returns_empty_portfolio(self):
        exchange = InMemoryPaperExchange()
        paper_submit_payload(
            ORDER,
            config=RuntimeConfig(autonomy_stage=AutonomyStage.HUMAN_APPROVAL),
            exchange=exchange,
        )

        payload = paper_reset_payload(exchange=exchange)

        self.assertTrue(payload["reset"])
        self.assertEqual(payload["portfolio"]["exposure"]["gross_exposure"], "0")

    def test_strategy_api_start_pause_stop(self):
        manager = StrategySessionManager()

        started = strategy_start_payload({}, manager=manager)
        paused = strategy_pause_payload({}, manager=manager)
        stopped = strategy_stop_payload({}, manager=manager)

        self.assertEqual(started["session"]["status"], "running")
        self.assertEqual(started["recommendations"][0]["action"], "NO_TRADE")
        self.assertEqual(paused["session"]["status"], "paused")
        self.assertEqual(stopped["session"]["status"], "stopped")


if __name__ == "__main__":
    unittest.main()
