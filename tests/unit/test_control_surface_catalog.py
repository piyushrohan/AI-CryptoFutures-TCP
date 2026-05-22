import unittest

from libs.config import OperatorMode, VenueTarget
from libs.schemas import (
    CommandEffect,
    CommandType,
    all_command_definitions,
    catalog_validation_errors,
    command_definition,
    control_surface_payload,
)


class ControlSurfaceCatalogTests(unittest.TestCase):
    def test_catalog_is_internally_valid(self):
        self.assertEqual(catalog_validation_errors(), [])

    def test_required_phase_zero_actions_are_mapped(self):
        actions = " ".join(
            f"{item.screen} {item.operator_action}".lower()
            for item in all_command_definitions()
        )

        for keyword in (
            "observe",
            "account-state",
            "paper",
            "testnet",
            "symbol metadata",
            "fee policy",
            "training",
            "evaluation",
            "backtest",
            "strategy",
            "model deployment",
            "manual order",
            "approve",
            "reject",
            "panic cancel",
            "panic flatten",
            "audit",
        ):
            self.assertIn(keyword, actions)

    def test_frontend_primary_modes_are_paper_and_live_only(self):
        payload = control_surface_payload()

        self.assertEqual(
            payload["primary_operator_modes"],
            [OperatorMode.PAPER.value, OperatorMode.LIVE.value],
        )
        self.assertEqual(
            payload["internal_lanes"]["testnet"],
            VenueTarget.BINANCE_TESTNET.value,
        )

    def test_catalog_does_not_target_exchange_connector_directly(self):
        owners = {item.owner.value for item in all_command_definitions()}

        self.assertNotIn("exchange_connector", owners)
        self.assertNotIn("binance_connector", owners)

    def test_live_trading_commands_are_cataloged_but_not_executable(self):
        live_commands = [
            item
            for item in all_command_definitions()
            if item.effect == CommandEffect.LIVE_TRADING
        ]

        self.assertGreaterEqual(len(live_commands), 1)
        self.assertTrue(all(not item.execution_available for item in live_commands))

    def test_strategy_sessions_require_fee_model(self):
        definition = command_definition(CommandType.CREATE_STRATEGY_SESSION)

        self.assertTrue(definition.requires_fee_model)
        self.assertFalse(definition.execution_available)


if __name__ == "__main__":
    unittest.main()
