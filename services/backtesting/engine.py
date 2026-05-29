"""Deterministic microstructure backtest scaffolding."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from libs.schemas import decimal_str, default_fee_policies
from services.market_data import MarketDepthSnapshot, generate_microstructure_features
from services.storage import JsonStateStore


@dataclass(frozen=True)
class BacktestReport:
    run_id: str
    fixture_source: str
    observation_count: int
    quote_count: int
    simulated_fill_count: int
    maker_order_count: int
    taker_order_count: int
    maker_taker_ratio: Decimal
    fill_ratio: Decimal
    fees_paid: Decimal
    adverse_selection_cost: Decimal
    missed_fill_count: int
    average_latency_ms: Decimal
    expected_edge_after_costs: Decimal
    approval_state: str

    def to_public_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "fixture_source": self.fixture_source,
            "observation_count": self.observation_count,
            "quote_count": self.quote_count,
            "simulated_fill_count": self.simulated_fill_count,
            "maker_order_count": self.maker_order_count,
            "taker_order_count": self.taker_order_count,
            "maker_taker_ratio": decimal_str(self.maker_taker_ratio),
            "fill_ratio": decimal_str(self.fill_ratio),
            "fees_paid": decimal_str(self.fees_paid),
            "adverse_selection_cost": decimal_str(self.adverse_selection_cost),
            "missed_fill_count": self.missed_fill_count,
            "average_latency_ms": decimal_str(self.average_latency_ms),
            "expected_edge_after_costs": decimal_str(
                self.expected_edge_after_costs
            ),
            "approval_state": self.approval_state,
            "notes": [
                "deterministic fixture backtest",
                "not live-trading approval",
                "no Binance connectivity",
            ],
        }


def run_microstructure_backtest(
    snapshots: tuple[MarketDepthSnapshot, ...] | None = None,
    *,
    run_id: str = "synthetic-microstructure-backtest-001",
) -> BacktestReport:
    features = generate_microstructure_features(snapshots)
    quote_count = len(features)
    simulated_fill_count = sum(
        1
        for row in features
        if row.order_book_imbalance > Decimal("0")
    )
    maker_order_count = quote_count
    taker_order_count = 0
    maker_taker_ratio = Decimal("1") if quote_count else Decimal("0")
    fill_ratio = (
        Decimal(simulated_fill_count) / Decimal(quote_count)
        if quote_count
        else Decimal("0")
    )
    fee_rate = default_fee_policies()[0].maker_fee_rate
    fees_paid = Decimal(simulated_fill_count) * Decimal("1000") * fee_rate
    adverse_selection_cost = sum(
        abs(row.latency_adjusted_return_bps)
        for row in features
    ) * Decimal("0.01")
    missed_fill_count = quote_count - simulated_fill_count
    average_latency_ms = (
        sum(
            Decimal(row.leg_timestamp_skew_ms or 0)
            for row in features
        )
        / Decimal(quote_count)
        if quote_count
        else Decimal("0")
    )
    gross_edge = Decimal(simulated_fill_count) * Decimal("0.9")
    expected_edge_after_costs = gross_edge - fees_paid - adverse_selection_cost
    return BacktestReport(
        run_id=run_id,
        fixture_source=(
            "local_replay_file" if snapshots is not None else "synthetic_in_repo_fixture"
        ),
        observation_count=len(features),
        quote_count=quote_count,
        simulated_fill_count=simulated_fill_count,
        maker_order_count=maker_order_count,
        taker_order_count=taker_order_count,
        maker_taker_ratio=maker_taker_ratio,
        fill_ratio=fill_ratio,
        fees_paid=fees_paid,
        adverse_selection_cost=adverse_selection_cost,
        missed_fill_count=missed_fill_count,
        average_latency_ms=average_latency_ms,
        expected_edge_after_costs=expected_edge_after_costs,
        approval_state="research_only",
    )


def persist_backtest_report(
    report: BacktestReport,
    store: JsonStateStore | None = None,
) -> None:
    selected_store = store or JsonStateStore()
    payload = report.to_public_dict()
    selected_store.write_json("backtests/latest_report.json", payload)
    selected_store.append_jsonl("backtests/reports.jsonl", payload)


def backtest_report_payload(
    snapshots: tuple[MarketDepthSnapshot, ...] | None = None,
    *,
    persist: bool = True,
) -> dict[str, object]:
    report = run_microstructure_backtest(snapshots)
    if persist:
        persist_backtest_report(report)
    return {
        "status": "ok",
        "service": "backtesting",
        "report": report.to_public_dict(),
    }
