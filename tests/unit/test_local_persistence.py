from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from libs.config import RuntimeConfig
from libs.schemas import PaperOrderIntent, default_account_state
from services.audit import FileBackedAuditRecorder
from services.market_data import FileBackedExchangeStateStore
from services.paper_exchange import InMemoryPaperExchange, PaperExchangeStateStore
from services.storage import JsonStateStore


class LocalPersistenceTests(unittest.TestCase):
    def test_file_backed_audit_recorder_persists_redacted_records(self):
        with TemporaryDirectory() as tmp:
            store = JsonStateStore(tmp)
            recorder = FileBackedAuditRecorder(store)

            recorder.record_decision(
                command_type="submit_paper_order",
                actor_id="tester",
                decision="accepted",
                reasons=[],
                payload={"symbol": "BTCUSDC", "api_secret": "never-store"},
                runtime=RuntimeConfig().to_status(),
            )
            reloaded = FileBackedAuditRecorder(store)

            self.assertEqual(len(reloaded.records()), 1)
            persisted = Path(tmp, "audit", "records.jsonl").read_text()
            self.assertIn("api_secret", persisted)
            self.assertNotIn("never-store", persisted)
            self.assertNotIn("BTCUSDC", persisted)

    def test_paper_exchange_persists_orders_portfolio_and_reconciliation(self):
        with TemporaryDirectory() as tmp:
            state_store = PaperExchangeStateStore(JsonStateStore(tmp))
            exchange = InMemoryPaperExchange(state_store=state_store)

            exchange.submit_order(
                PaperOrderIntent.from_mapping(
                    {
                        "symbol": "BTCUSDC",
                        "side": "BUY",
                        "book_side": "LONG",
                        "quantity": "0.001",
                        "limit_price": "64999.9",
                    }
                )
            )

            self.assertTrue(Path(tmp, "paper", "orders.json").exists())
            self.assertTrue(Path(tmp, "paper", "portfolio.json").exists())
            self.assertTrue(Path(tmp, "paper", "reconciliation.json").exists())
            self.assertTrue(Path(tmp, "paper", "latest.json").exists())

    def test_file_backed_exchange_state_store_persists_snapshot(self):
        with TemporaryDirectory() as tmp:
            store = FileBackedExchangeStateStore(
                default_account_state(),
                JsonStateStore(tmp),
            )

            store.append(default_account_state())

            self.assertTrue(
                Path(tmp, "exchange", "latest_account_state.json").exists()
            )
            self.assertTrue(
                Path(tmp, "exchange", "account_state_snapshots.jsonl").exists()
            )


if __name__ == "__main__":
    unittest.main()
