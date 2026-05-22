from datetime import UTC, datetime, timedelta
from decimal import Decimal
import unittest

from libs.schemas import (
    AccountState,
    BookSide,
    FeePolicy,
    FeePromotion,
    MarginMode,
    PositionMode,
    default_account_state,
    default_fee_policies,
    default_symbol_metadata,
    stale_freshness,
)
from services.market_data import InMemoryExchangeStateStore, exchange_state_payload


REFERENCE_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


class ExchangeStateTests(unittest.TestCase):
    def test_default_account_state_is_valid_and_local_only(self):
        state = default_account_state(REFERENCE_TIME)

        self.assertEqual(state.margin_mode, MarginMode.CROSS)
        self.assertEqual(state.position_mode, PositionMode.HEDGE)
        self.assertFalse(state.portfolio_margin_enabled)
        self.assertEqual(state.open_orders, ())
        self.assertEqual(state.validation_errors(REFERENCE_TIME), [])

    def test_hedge_mode_has_independent_long_and_short_books(self):
        state = default_account_state(REFERENCE_TIME)
        books = {(book.symbol, book.side) for book in state.position_books}

        for symbol in ("BTCUSDC", "ETHUSDC"):
            self.assertIn((symbol, BookSide.LONG), books)
            self.assertIn((symbol, BookSide.SHORT), books)

    def test_missing_hedge_book_is_rejected(self):
        state = default_account_state(REFERENCE_TIME)
        incomplete = AccountState(
            **{
                **state.__dict__,
                "position_books": tuple(
                    book
                    for book in state.position_books
                    if not (
                        book.symbol == "BTCUSDC"
                        and book.side == BookSide.SHORT
                    )
                ),
            }
        )

        self.assertIn(
            "BTCUSDC missing hedge SHORT book",
            incomplete.validation_errors(REFERENCE_TIME),
        )

    def test_portfolio_margin_enabled_is_rejected_in_phase_two(self):
        state = default_account_state(REFERENCE_TIME)
        portfolio_margin = AccountState(
            **{
                **state.__dict__,
                "margin_mode": MarginMode.PORTFOLIO_MARGIN,
                "portfolio_margin_enabled": True,
            }
        )

        self.assertIn(
            "Portfolio Margin is research-only in Phase 2",
            portfolio_margin.validation_errors(REFERENCE_TIME),
        )

    def test_symbol_metadata_contains_filters_for_executable_symbols_only(self):
        metadata = {item.symbol: item for item in default_symbol_metadata(REFERENCE_TIME)}

        self.assertIsNotNone(metadata["BTCUSDC"].filters)
        self.assertIsNotNone(metadata["ETHUSDC"].filters)
        self.assertIsNone(metadata["SYN_ETHBTC"].filters)
        self.assertIsNone(metadata["ETHBTC"].filters)
        self.assertEqual(metadata["BTCUSDC"].validation_errors(REFERENCE_TIME), [])
        self.assertEqual(metadata["ETHUSDC"].validation_errors(REFERENCE_TIME), [])

    def test_stale_symbol_metadata_is_rejected(self):
        metadata = default_symbol_metadata(REFERENCE_TIME)[0]
        stale = type(metadata)(
            **{
                **metadata.__dict__,
                "freshness": stale_freshness(REFERENCE_TIME),
            }
        )

        self.assertIn(
            "BTCUSDC is stale",
            stale.validation_errors(REFERENCE_TIME),
        )

    def test_default_fee_policies_are_nonzero_and_valid(self):
        policies = default_fee_policies(REFERENCE_TIME)

        self.assertEqual({item.symbol for item in policies}, {"BTCUSDC", "ETHUSDC"})
        for policy in policies:
            self.assertGreater(policy.maker_fee_rate, Decimal("0"))
            self.assertGreater(policy.taker_fee_rate, Decimal("0"))
            self.assertEqual(policy.validation_errors(REFERENCE_TIME), [])

    def test_zero_maker_fee_requires_time_bounded_promotion(self):
        base = default_fee_policies(REFERENCE_TIME)[0]
        unsafe_zero = FeePolicy(
            **{
                **base.__dict__,
                "maker_fee_rate": Decimal("0"),
                "promotion": None,
            }
        )

        self.assertIn(
            "BTCUSDC zero maker fee requires time-bounded promotion metadata",
            unsafe_zero.validation_errors(REFERENCE_TIME),
        )

    def test_time_bounded_zero_maker_fee_promotion_is_allowed(self):
        base = default_fee_policies(REFERENCE_TIME)[0]
        promoted = FeePolicy(
            **{
                **base.__dict__,
                "maker_fee_rate": Decimal("0"),
                "promotion": FeePromotion(
                    source="research_override",
                    effective_from=REFERENCE_TIME,
                    effective_until=REFERENCE_TIME + timedelta(days=1),
                    review_at=REFERENCE_TIME + timedelta(hours=12),
                    approval_reference="paper-research-approval",
                    fallback_maker_fee_rate=Decimal("0.000100"),
                ),
            }
        )

        self.assertEqual(promoted.validation_errors(REFERENCE_TIME), [])

    def test_exchange_state_payload_is_read_only_and_valid(self):
        payload = exchange_state_payload(REFERENCE_TIME)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["service"], "exchange_state")
        self.assertTrue(payload["account_state"]["is_valid"])
        self.assertIn("no Binance connectivity", payload["notes"])
        self.assertIn("no order submission", payload["notes"])

    def test_in_memory_snapshot_store_keeps_latest_snapshot(self):
        first = default_account_state(REFERENCE_TIME)
        second = default_account_state(REFERENCE_TIME + timedelta(seconds=1))
        store = InMemoryExchangeStateStore(first)

        store.append(second)

        self.assertEqual(store.latest(), second)
        self.assertEqual(len(store.snapshots()), 2)


if __name__ == "__main__":
    unittest.main()
