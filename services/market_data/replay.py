"""Synthetic BTC/ETH replay fixtures and microstructure features."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from libs.schemas import decimal_str


@dataclass(frozen=True)
class MarketDepthSnapshot:
    symbol: str
    timestamp: datetime
    receive_timestamp: datetime
    bid: Decimal
    ask: Decimal
    bid_size: Decimal
    ask_size: Decimal
    buy_trade_qty: Decimal
    sell_trade_qty: Decimal
    funding_rate_bps: Decimal
    open_interest: Decimal
    liquidation_notional: Decimal
    latency_ms: int

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / Decimal("2")

    @property
    def spread(self) -> Decimal:
        return self.ask - self.bid

    def to_public_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "receive_timestamp": self.receive_timestamp.isoformat(),
            "bid": decimal_str(self.bid),
            "ask": decimal_str(self.ask),
            "bid_size": decimal_str(self.bid_size),
            "ask_size": decimal_str(self.ask_size),
            "mid": decimal_str(self.mid),
            "spread": decimal_str(self.spread),
            "buy_trade_qty": decimal_str(self.buy_trade_qty),
            "sell_trade_qty": decimal_str(self.sell_trade_qty),
            "funding_rate_bps": decimal_str(self.funding_rate_bps),
            "open_interest": decimal_str(self.open_interest),
            "liquidation_notional": decimal_str(self.liquidation_notional),
            "latency_ms": self.latency_ms,
        }


@dataclass(frozen=True)
class SyntheticEthBtcSnapshot:
    timestamp: datetime
    synthetic_mid: Decimal
    synthetic_bid: Decimal
    synthetic_ask: Decimal
    synthetic_spread: Decimal
    leg_timestamp_skew_ms: int
    is_stale: bool

    def to_public_dict(self) -> dict[str, object]:
        return {
            "symbol": "SYN_ETHBTC",
            "timestamp": self.timestamp.isoformat(),
            "synthetic_mid": decimal_str(self.synthetic_mid),
            "synthetic_bid": decimal_str(self.synthetic_bid),
            "synthetic_ask": decimal_str(self.synthetic_ask),
            "synthetic_spread": decimal_str(self.synthetic_spread),
            "leg_timestamp_skew_ms": self.leg_timestamp_skew_ms,
            "is_stale": self.is_stale,
        }


@dataclass(frozen=True)
class MicrostructureFeatureRow:
    timestamp: datetime
    symbol: str
    order_book_imbalance: Decimal
    microprice: Decimal
    spread: Decimal
    depth_slope: Decimal
    queue_imbalance: Decimal
    trade_aggression: Decimal
    short_horizon_return_bps: Decimal
    realized_volatility_bps: Decimal
    funding_rate_bps: Decimal
    open_interest: Decimal
    liquidation_notional: Decimal
    latency_adjusted_return_bps: Decimal
    synthetic_ethbtc_mid: Decimal | None = None
    synthetic_spread_cost: Decimal | None = None
    leg_timestamp_skew_ms: int | None = None

    def to_public_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "order_book_imbalance": decimal_str(self.order_book_imbalance),
            "microprice": decimal_str(self.microprice),
            "spread": decimal_str(self.spread),
            "depth_slope": decimal_str(self.depth_slope),
            "queue_imbalance": decimal_str(self.queue_imbalance),
            "trade_aggression": decimal_str(self.trade_aggression),
            "short_horizon_return_bps": decimal_str(
                self.short_horizon_return_bps
            ),
            "realized_volatility_bps": decimal_str(
                self.realized_volatility_bps
            ),
            "funding_rate_bps": decimal_str(self.funding_rate_bps),
            "open_interest": decimal_str(self.open_interest),
            "liquidation_notional": decimal_str(self.liquidation_notional),
            "latency_adjusted_return_bps": decimal_str(
                self.latency_adjusted_return_bps
            ),
            "synthetic_ethbtc_mid": (
                decimal_str(self.synthetic_ethbtc_mid)
                if self.synthetic_ethbtc_mid is not None
                else None
            ),
            "synthetic_spread_cost": (
                decimal_str(self.synthetic_spread_cost)
                if self.synthetic_spread_cost is not None
                else None
            ),
            "leg_timestamp_skew_ms": self.leg_timestamp_skew_ms,
        }


def synthetic_market_depth_fixtures() -> tuple[MarketDepthSnapshot, ...]:
    base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    rows: list[MarketDepthSnapshot] = []
    values = (
        ("BTCUSDC", "65000.0", "65000.5", "4.2", "3.8", "1.1", "0.8", "0.8", "120000", "0", 24),
        ("ETHUSDC", "3200.00", "3200.05", "90", "84", "18", "14", "0.6", "890000", "0", 19),
        ("BTCUSDC", "65010.0", "65010.5", "3.7", "4.4", "0.7", "1.0", "0.8", "120500", "15000", 26),
        ("ETHUSDC", "3202.00", "3202.05", "86", "92", "12", "18", "0.6", "891000", "8000", 22),
        ("BTCUSDC", "65005.0", "65005.4", "4.8", "3.5", "1.4", "0.9", "0.8", "120200", "0", 21),
        ("ETHUSDC", "3201.40", "3201.45", "94", "80", "20", "13", "0.6", "891500", "0", 18),
    )
    for index, item in enumerate(values):
        timestamp = base + timedelta(seconds=index // 2)
        rows.append(
            MarketDepthSnapshot(
                symbol=item[0],
                timestamp=timestamp,
                receive_timestamp=timestamp + timedelta(milliseconds=int(item[10])),
                bid=Decimal(item[1]),
                ask=Decimal(item[2]),
                bid_size=Decimal(item[3]),
                ask_size=Decimal(item[4]),
                buy_trade_qty=Decimal(item[5]),
                sell_trade_qty=Decimal(item[6]),
                funding_rate_bps=Decimal(item[7]),
                open_interest=Decimal(item[8]),
                liquidation_notional=Decimal(item[9]),
                latency_ms=int(item[10]),
            )
        )
    return tuple(rows)


def _parse_timestamp(value: object) -> datetime:
    if value in (None, ""):
        return datetime.now(UTC)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _snapshot_from_mapping(row: Mapping[str, Any]) -> MarketDepthSnapshot:
    timestamp = _parse_timestamp(row.get("timestamp"))
    receive_timestamp = _parse_timestamp(row.get("receive_timestamp", timestamp.isoformat()))
    latency_ms = int(row.get("latency_ms", max(
        0,
        int((receive_timestamp - timestamp).total_seconds() * 1000),
    )))
    return MarketDepthSnapshot(
        symbol=str(row["symbol"]),
        timestamp=timestamp,
        receive_timestamp=receive_timestamp,
        bid=Decimal(str(row["bid"])),
        ask=Decimal(str(row["ask"])),
        bid_size=Decimal(str(row.get("bid_size", "1"))),
        ask_size=Decimal(str(row.get("ask_size", "1"))),
        buy_trade_qty=Decimal(str(row.get("buy_trade_qty", "0"))),
        sell_trade_qty=Decimal(str(row.get("sell_trade_qty", "0"))),
        funding_rate_bps=Decimal(str(row.get("funding_rate_bps", "0"))),
        open_interest=Decimal(str(row.get("open_interest", "0"))),
        liquidation_notional=Decimal(str(row.get("liquidation_notional", "0"))),
        latency_ms=latency_ms,
    )


def load_replay_file(path: str | Path) -> tuple[MarketDepthSnapshot, ...]:
    replay_path = Path(path)
    if replay_path.suffix.lower() == ".json":
        loaded = json.loads(replay_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, list):
            raise ValueError("replay JSON must contain a list of snapshot objects")
        rows = loaded
    else:
        with replay_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

    snapshots = tuple(_snapshot_from_mapping(row) for row in rows)
    symbols = {item.symbol for item in snapshots}
    forbidden = symbols - {"BTCUSDC", "ETHUSDC"}
    if forbidden:
        raise ValueError(
            "local replay files may only contain BTCUSDC and ETHUSDC snapshots"
        )
    return snapshots


def derive_synthetic_ethbtc(
    eth: MarketDepthSnapshot,
    btc: MarketDepthSnapshot,
    *,
    stale_after_ms: int = 250,
) -> SyntheticEthBtcSnapshot:
    skew_ms = int(abs((eth.receive_timestamp - btc.receive_timestamp).total_seconds()) * 1000)
    synthetic_bid = eth.bid / btc.ask
    synthetic_ask = eth.ask / btc.bid
    synthetic_mid = eth.mid / btc.mid
    return SyntheticEthBtcSnapshot(
        timestamp=max(eth.timestamp, btc.timestamp),
        synthetic_mid=synthetic_mid,
        synthetic_bid=synthetic_bid,
        synthetic_ask=synthetic_ask,
        synthetic_spread=synthetic_ask - synthetic_bid,
        leg_timestamp_skew_ms=skew_ms,
        is_stale=skew_ms > stale_after_ms,
    )


def _feature_for_snapshot(
    snapshot: MarketDepthSnapshot,
    previous: MarketDepthSnapshot | None,
    synthetic: SyntheticEthBtcSnapshot | None,
) -> MicrostructureFeatureRow:
    depth_total = snapshot.bid_size + snapshot.ask_size
    trade_total = snapshot.buy_trade_qty + snapshot.sell_trade_qty
    imbalance = (
        (snapshot.bid_size - snapshot.ask_size) / depth_total
        if depth_total > 0
        else Decimal("0")
    )
    microprice = (
        (snapshot.ask * snapshot.bid_size + snapshot.bid * snapshot.ask_size)
        / depth_total
        if depth_total > 0
        else snapshot.mid
    )
    trade_aggression = (
        (snapshot.buy_trade_qty - snapshot.sell_trade_qty) / trade_total
        if trade_total > 0
        else Decimal("0")
    )
    short_return = Decimal("0")
    if previous is not None and previous.mid > 0:
        short_return = (snapshot.mid - previous.mid) / previous.mid * Decimal("10000")
    latency_penalty = Decimal(snapshot.latency_ms) * Decimal("0.01")
    synthetic_mid = synthetic.synthetic_mid if synthetic else None
    synthetic_spread = synthetic.synthetic_spread if synthetic else None
    return MicrostructureFeatureRow(
        timestamp=snapshot.timestamp,
        symbol=snapshot.symbol,
        order_book_imbalance=imbalance,
        microprice=microprice,
        spread=snapshot.spread,
        depth_slope=(snapshot.ask_size - snapshot.bid_size) / depth_total,
        queue_imbalance=imbalance,
        trade_aggression=trade_aggression,
        short_horizon_return_bps=short_return,
        realized_volatility_bps=abs(short_return),
        funding_rate_bps=snapshot.funding_rate_bps,
        open_interest=snapshot.open_interest,
        liquidation_notional=snapshot.liquidation_notional,
        latency_adjusted_return_bps=short_return - latency_penalty,
        synthetic_ethbtc_mid=synthetic_mid,
        synthetic_spread_cost=synthetic_spread,
        leg_timestamp_skew_ms=synthetic.leg_timestamp_skew_ms if synthetic else None,
    )


def generate_microstructure_features(
    snapshots: tuple[MarketDepthSnapshot, ...] | None = None,
) -> tuple[MicrostructureFeatureRow, ...]:
    rows = snapshots or synthetic_market_depth_fixtures()
    by_symbol_previous: dict[str, MarketDepthSnapshot] = {}
    by_time: dict[datetime, dict[str, MarketDepthSnapshot]] = {}
    for snapshot in rows:
        by_time.setdefault(snapshot.timestamp, {})[snapshot.symbol] = snapshot

    features: list[MicrostructureFeatureRow] = []
    for snapshot in rows:
        synthetic = None
        siblings = by_time.get(snapshot.timestamp, {})
        if "ETHUSDC" in siblings and "BTCUSDC" in siblings:
            synthetic = derive_synthetic_ethbtc(
                siblings["ETHUSDC"],
                siblings["BTCUSDC"],
            )
        previous = by_symbol_previous.get(snapshot.symbol)
        features.append(_feature_for_snapshot(snapshot, previous, synthetic))
        by_symbol_previous[snapshot.symbol] = snapshot
    return tuple(features)


def replay_payload(
    snapshots: tuple[MarketDepthSnapshot, ...] | None = None,
    *,
    source: str = "synthetic_in_repo_fixture",
) -> dict[str, object]:
    snapshots = snapshots or synthetic_market_depth_fixtures()
    features = generate_microstructure_features(snapshots)
    synthetic = [
        derive_synthetic_ethbtc(
            item["ETHUSDC"],
            item["BTCUSDC"],
        ).to_public_dict()
        for item in {
            row.timestamp: {
                snapshot.symbol: snapshot
                for snapshot in snapshots
                if snapshot.timestamp == row.timestamp
            }
            for row in snapshots
        }.values()
        if "ETHUSDC" in item and "BTCUSDC" in item
    ]
    return {
        "status": "ok",
        "service": "market_data_replay",
        "source": source,
        "notes": [
            "no downloaded market data",
            "BTCUSDC and ETHUSDC only",
            "SYN_ETHBTC is derived and non-executable",
        ],
        "snapshots": [item.to_public_dict() for item in snapshots],
        "synthetic_ethbtc": synthetic,
        "features": [item.to_public_dict() for item in features],
    }
