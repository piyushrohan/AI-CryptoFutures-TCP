from datetime import UTC, datetime
from decimal import Decimal
import unittest

from libs.schemas import (
    AccountState,
    BookSide,
    OrderSide,
    PaperMarketQuote,
    PaperOrderIntent,
    stale_freshness,
)
from libs.config import AutonomyStage, RuntimeConfig
from services.paper_exchange import InMemoryPaperExchange
from services.portfolio import calculate_portfolio_exposure
from services.risk import PaperRiskState, RiskLimits, evaluate_paper_order_risk


REFERENCE_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def btc_buy_long() -> PaperOrderIntent:
    return PaperOrderIntent.from_mapping(
        {
            "symbol": "BTCUSDC",
            "side": "BUY",
            "book_side": "LONG",
            "quantity": "0.001",
            "limit_price": "65000.4",
        }
    )


class PaperTradingTests(unittest.TestCase):
    def test_preview_and_submit_paper_order(self):
        exchange = InMemoryPaperExchange()
        intent = btc_buy_long()

        preview = exchange.preview_order(intent, reference_time=REFERENCE_TIME)
        result = exchange.submit_order(intent, reference_time=REFERENCE_TIME)

        self.assertTrue(preview.accepted)
        self.assertTrue(result.accepted)
        self.assertEqual(result.order.status.value, "NEW")
        processed = exchange.process_open_orders(reference_time=REFERENCE_TIME)
        self.assertEqual(processed["processed"][0]["status"], "FILLED")
        self.assertEqual(
            exchange.portfolio_payload()["exposure"]["gross_exposure"],
            "65.0004",
        )

    def test_post_only_crossing_is_rejected(self):
        exchange = InMemoryPaperExchange()
        intent = PaperOrderIntent.from_mapping(
            {
                "symbol": "BTCUSDC",
                "side": "BUY",
                "book_side": "LONG",
                "quantity": "0.001",
                "limit_price": "65000.5",
            }
        )

        preview = exchange.preview_order(intent, reference_time=REFERENCE_TIME)

        self.assertFalse(preview.accepted)
        self.assertIn("post-only order would cross the paper book", preview.reasons)

    def test_taker_behavior_requires_gate(self):
        exchange = InMemoryPaperExchange()
        intent = PaperOrderIntent.from_mapping(
            {
                "symbol": "BTCUSDC",
                "side": "BUY",
                "book_side": "LONG",
                "quantity": "0.001",
                "limit_price": "64999.9",
                "allow_taker": True,
            }
        )

        preview = exchange.preview_order(intent, reference_time=REFERENCE_TIME)

        self.assertFalse(preview.accepted)
        self.assertIn(
            "taker behavior is not enabled for paper exchange",
            preview.reasons,
        )

    def test_resting_order_can_partially_fill_and_cancel(self):
        exchange = InMemoryPaperExchange()
        intent = PaperOrderIntent.from_mapping(
            {
                "symbol": "BTCUSDC",
                "side": "BUY",
                "book_side": "LONG",
                "quantity": "0.002",
                "limit_price": "64999.9",
            }
        )
        result = exchange.submit_order(intent, reference_time=REFERENCE_TIME)

        processed = exchange.process_open_orders(reference_time=REFERENCE_TIME)
        canceled = exchange.cancel_order(result.order.order_id)

        self.assertEqual(result.order.status.value, "NEW")
        self.assertEqual(processed["processed"][0]["status"], "PARTIALLY_FILLED")
        self.assertTrue(canceled["canceled"])
        self.assertEqual(exchange.orders()[0].status.value, "CANCELED")

    def test_resting_order_can_expire(self):
        exchange = InMemoryPaperExchange()
        result = exchange.submit_order(
            PaperOrderIntent.from_mapping(
                {
                    "symbol": "BTCUSDC",
                    "side": "BUY",
                    "book_side": "LONG",
                    "quantity": "0.001",
                    "limit_price": "64999.9",
                }
            ),
            reference_time=REFERENCE_TIME,
        )

        expired = exchange.expire_order(result.order.order_id)

        self.assertTrue(expired["expired"])
        self.assertEqual(exchange.orders()[0].status.value, "EXPIRED")

    def test_short_book_does_not_close_long_book(self):
        exchange = InMemoryPaperExchange()
        exchange.submit_order(btc_buy_long(), reference_time=REFERENCE_TIME)
        exchange.process_open_orders(reference_time=REFERENCE_TIME)
        exchange.submit_order(
            PaperOrderIntent.from_mapping(
                {
                    "symbol": "BTCUSDC",
                    "side": "SELL",
                    "book_side": "SHORT",
                    "quantity": "0.001",
                    "limit_price": "65000.4",
                }
            ),
            reference_time=REFERENCE_TIME,
        )
        exchange.process_open_orders(reference_time=REFERENCE_TIME)
        books = {
            (book.symbol, book.side): book
            for book in exchange.account_state().position_books
        }

        self.assertEqual(
            books[("BTCUSDC", BookSide.LONG)].quantity,
            Decimal("0.001"),
        )
        self.assertEqual(
            books[("BTCUSDC", BookSide.SHORT)].quantity,
            Decimal("0.001"),
        )

    def test_stale_quote_vetoes_risk(self):
        exchange = InMemoryPaperExchange()
        intent = btc_buy_long()
        preview = exchange.preview_order(intent, reference_time=REFERENCE_TIME)
        quote = exchange.quote_for_symbol("BTCUSDC", REFERENCE_TIME)
        stale_quote = PaperMarketQuote(
            **{
                **quote.__dict__,
                "freshness": stale_freshness(REFERENCE_TIME),
            }
        )

        result = evaluate_paper_order_risk(
            exchange.account_state(),
            intent,
            preview,
            stale_quote,
            reference_time=REFERENCE_TIME,
        )

        self.assertFalse(result.accepted)
        self.assertIn("BTCUSDC quote is stale", result.reasons)

    def test_max_symbol_exposure_vetoes_order(self):
        exchange = InMemoryPaperExchange()
        intent = btc_buy_long()
        preview = exchange.preview_order(intent, reference_time=REFERENCE_TIME)
        quote = exchange.quote_for_symbol("BTCUSDC", REFERENCE_TIME)

        result = evaluate_paper_order_risk(
            exchange.account_state(),
            intent,
            preview,
            quote,
            limits=RiskLimits(max_symbol_exposure=Decimal("10")),
            reference_time=REFERENCE_TIME,
        )

        self.assertFalse(result.accepted)
        self.assertIn("max symbol exposure would be exceeded", result.reasons)

    def test_portfolio_exposure_includes_beta_sector_and_leg_imbalance(self):
        exchange = InMemoryPaperExchange()
        exchange.submit_order(btc_buy_long(), reference_time=REFERENCE_TIME)
        exchange.process_open_orders(reference_time=REFERENCE_TIME)

        exposure = calculate_portfolio_exposure(exchange.account_state())

        self.assertEqual(exposure.sector_exposure, Decimal("65.0004"))
        self.assertEqual(exposure.correlated_exposure, Decimal("65.0004"))
        self.assertEqual(exposure.beta_exposure, Decimal("65.0004"))
        self.assertEqual(exposure.leg_imbalance, Decimal("65.0004"))

    def test_sector_correlation_beta_and_leg_limits_veto_order(self):
        exchange = InMemoryPaperExchange()
        intent = btc_buy_long()
        preview = exchange.preview_order(intent, reference_time=REFERENCE_TIME)
        quote = exchange.quote_for_symbol("BTCUSDC", REFERENCE_TIME)

        result = evaluate_paper_order_risk(
            exchange.account_state(),
            intent,
            preview,
            quote,
            limits=RiskLimits(
                max_sector_exposure=Decimal("10"),
                max_correlated_exposure=Decimal("10"),
                max_beta_exposure=Decimal("10"),
                max_leg_imbalance=Decimal("10"),
            ),
            reference_time=REFERENCE_TIME,
        )

        self.assertFalse(result.accepted)
        self.assertIn("max sector exposure would be exceeded", result.reasons)
        self.assertIn("max correlated exposure would be exceeded", result.reasons)
        self.assertIn("max beta exposure would be exceeded", result.reasons)
        self.assertIn("max leg imbalance would be exceeded", result.reasons)

    def test_kill_switch_states_veto_orders(self):
        exchange = InMemoryPaperExchange()
        intent = btc_buy_long()
        preview = exchange.preview_order(intent, reference_time=REFERENCE_TIME)
        quote = exchange.quote_for_symbol("BTCUSDC", REFERENCE_TIME)

        result = evaluate_paper_order_risk(
            exchange.account_state(),
            intent,
            preview,
            quote,
            state=PaperRiskState(
                daily_loss=Decimal("1000"),
                drawdown=Decimal("1500"),
                open_order_count_last_minute=10,
                api_error_active=True,
                panic_halt_active=True,
            ),
            reference_time=REFERENCE_TIME,
        )

        self.assertIn("panic halt is active", result.reasons)
        self.assertIn("API error kill switch is active", result.reasons)
        self.assertIn("max daily loss limit reached", result.reasons)
        self.assertIn("max drawdown limit reached", result.reasons)
        self.assertIn("order spam protection limit reached", result.reasons)

    def test_panic_halt_and_flatten_are_paper_only(self):
        exchange = InMemoryPaperExchange()
        exchange.submit_order(btc_buy_long(), reference_time=REFERENCE_TIME)
        exchange.process_open_orders(reference_time=REFERENCE_TIME)

        halt = exchange.panic_halt()
        flattened = exchange.panic_flatten_positions()

        self.assertTrue(halt["panic_halt"])
        self.assertTrue(flattened["flattened"])
        self.assertEqual(
            flattened["portfolio"]["exposure"]["gross_exposure"],
            "0",
        )


class PaperTradingApiConfigTests(unittest.TestCase):
    def test_runtime_human_approval_allows_paper_submit_command(self):
        from apps.api.server import paper_submit_payload

        payload = paper_submit_payload(
            btc_buy_long().to_public_dict(),
            config=RuntimeConfig(autonomy_stage=AutonomyStage.HUMAN_APPROVAL),
            exchange=InMemoryPaperExchange(),
        )

        self.assertEqual(payload["execution"], "paper_only")
        self.assertTrue(payload["paper_result"]["accepted"])


if __name__ == "__main__":
    unittest.main()
