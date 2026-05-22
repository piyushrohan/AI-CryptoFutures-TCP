import unittest

from services.backtesting import backtest_report_payload, run_microstructure_backtest
from services.market_data import (
    derive_synthetic_ethbtc,
    generate_microstructure_features,
    replay_payload,
    synthetic_market_depth_fixtures,
)
from services.strategy import StrategySessionManager


class ResearchBacktestStrategyTests(unittest.TestCase):
    def test_synthetic_ethbtc_is_derived_from_usdc_legs(self):
        snapshots = synthetic_market_depth_fixtures()
        btc = next(item for item in snapshots if item.symbol == "BTCUSDC")
        eth = next(item for item in snapshots if item.symbol == "ETHUSDC")

        synthetic = derive_synthetic_ethbtc(eth, btc)

        self.assertEqual(synthetic.to_public_dict()["symbol"], "SYN_ETHBTC")
        self.assertGreater(synthetic.synthetic_mid, 0)
        self.assertFalse(synthetic.is_stale)

    def test_microstructure_features_are_deterministic(self):
        first = generate_microstructure_features()
        second = generate_microstructure_features()

        self.assertEqual(
            [item.to_public_dict() for item in first],
            [item.to_public_dict() for item in second],
        )
        self.assertEqual(len(first), 6)

    def test_replay_payload_uses_synthetic_fixture_only(self):
        payload = replay_payload()

        self.assertEqual(payload["source"], "synthetic_in_repo_fixture")
        self.assertEqual(len(payload["snapshots"]), 6)
        self.assertEqual(len(payload["synthetic_ethbtc"]), 3)
        self.assertIn("no downloaded market data", payload["notes"])

    def test_backtest_report_has_cost_and_fill_metrics(self):
        report = run_microstructure_backtest()
        payload = backtest_report_payload()

        self.assertEqual(report.taker_order_count, 0)
        self.assertEqual(report.maker_taker_ratio, 1)
        self.assertIn("expected_edge_after_costs", payload["report"])
        self.assertEqual(payload["report"]["approval_state"], "research_only")

    def test_strategy_session_defaults_to_no_trade(self):
        manager = StrategySessionManager()
        session = manager.start_session()
        recommendation = manager.recommendations()[0]

        self.assertEqual(session.status.value, "running")
        self.assertEqual(recommendation.action, "NO_TRADE")
        self.assertEqual(recommendation.maker_or_taker_permission, "maker_only")
        self.assertIn(
            "strategy alpha is not implemented",
            recommendation.explanation,
        )

    def test_strategy_session_pause_and_stop(self):
        manager = StrategySessionManager()
        manager.start_session()

        paused = manager.pause_latest()
        stopped = manager.stop_latest()

        self.assertEqual(paused.status.value, "paused")
        self.assertEqual(stopped.status.value, "stopped")


if __name__ == "__main__":
    unittest.main()
