from pathlib import Path
import unittest

from libs.schemas import (
    DataRecordingLevel,
    InstrumentRole,
    derived_symbols,
    executable_symbols,
    reference_symbols,
    symbol_universe,
    symbol_universe_payload,
    symbol_universe_validation_errors,
)


class SymbolUniverseTests(unittest.TestCase):
    def test_initial_executable_universe_is_btc_and_eth_usdc_only(self):
        self.assertEqual(set(executable_symbols()), {"BTCUSDC", "ETHUSDC"})
        self.assertNotIn("ETHBTC", executable_symbols())
        self.assertNotIn("SYN_ETHBTC", executable_symbols())

    def test_synthetic_ethbtc_is_derived_and_not_executable(self):
        synthetic = {
            instrument.symbol: instrument for instrument in symbol_universe()
        }["SYN_ETHBTC"]

        self.assertEqual(synthetic.role, InstrumentRole.DERIVED)
        self.assertFalse(synthetic.execution_enabled)
        self.assertTrue(synthetic.enabled_by_default)
        self.assertEqual(synthetic.data_recording_level, DataRecordingLevel.DERIVED)
        self.assertEqual(synthetic.formula, "ETHUSDC / BTCUSDC")
        self.assertEqual(set(synthetic.components), {"ETHUSDC", "BTCUSDC"})

    def test_direct_ethbtc_is_disabled_reference_only(self):
        direct = {instrument.symbol: instrument for instrument in symbol_universe()}[
            "ETHBTC"
        ]

        self.assertEqual(direct.role, InstrumentRole.REFERENCE)
        self.assertFalse(direct.execution_enabled)
        self.assertFalse(direct.enabled_by_default)
        self.assertEqual(direct.data_recording_level, DataRecordingLevel.DISABLED)
        self.assertEqual(reference_symbols(), ("ETHBTC",))

    def test_universe_validation_passes(self):
        self.assertEqual(symbol_universe_validation_errors(), [])

    def test_public_payload_groups_roles(self):
        payload = symbol_universe_payload()

        self.assertEqual(set(payload["executable_symbols"]), {"BTCUSDC", "ETHUSDC"})
        self.assertEqual(derived_symbols(), ("SYN_ETHBTC",))
        self.assertEqual(payload["reference_symbols"], ["ETHBTC"])
        self.assertEqual(payload["validation_errors"], [])

    def test_config_file_documents_same_policy(self):
        text = Path("configs/symbol_universe.yml").read_text(encoding="utf-8")

        self.assertIn("symbol: BTCUSDC", text)
        self.assertIn("symbol: ETHUSDC", text)
        self.assertIn("symbol: SYN_ETHBTC", text)
        self.assertIn("symbol: ETHBTC", text)
        self.assertIn("formula: ETHUSDC / BTCUSDC", text)
        self.assertIn("execution_enabled: false", text)
        self.assertIn("Full ETHBTC order-book downloads are not required", text)


if __name__ == "__main__":
    unittest.main()
