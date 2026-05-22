# Three-Asset BTC/ETH Universe

AI-CryptoFutures-TCP should start with a deliberately small BTC/ETH universe. The first implementation should focus on executable `BTCUSDC` and `ETHUSDC` Binance USDⓈ-M Futures contracts, plus a derived `SYN_ETHBTC` research series.

This document is a design contract. It does not implement market data ingestion, strategy logic, Binance connectivity, or trading.

## Instrument Roles

| Symbol | Role | Execution | Data policy | Purpose |
| --- | --- | --- | --- | --- |
| `BTCUSDC` | executable | enabled after paper/risk gates | full recording | BTC beta anchor, hedge leg, market regime input |
| `ETHUSDC` | executable | enabled after paper/risk gates | full recording | ETH exposure leg, initial alpha candidate |
| `SYN_ETHBTC` | derived | never executable | computed from BTC/ETH USDC legs | ETH-vs-BTC relative-value signal |
| `ETHBTC` | reference | disabled | disabled by default; optional lightweight reference later | Direct-market benchmark only |

Executable means the platform may eventually produce order intents for the instrument after validation, risk, portfolio, execution, audit, and mode gates. Derived and reference instruments must not become executable without an explicit policy change, tests, and review.

## Why Not Trade ETHBTC First

The current product objective is a frontend-first, maker-first platform with dynamic fees, auditable expected edge, and conservative risk controls. Adding `ETHBTC` as a third executable instrument too early increases surface area:

- Separate symbol metadata, filters, tick size, lot size, and min notional checks.
- Separate fee, liquidity, funding, and fill-quality assumptions.
- Additional order book, replay, and storage requirements.
- More portfolio accounting complexity around quote asset and relative exposure.
- Higher risk that relative-value logic bypasses the two-leg portfolio model.

The MVP should prove the harder and more reusable primitive first: expressing ETH/BTC relative value through two executable USDC legs.

## Synthetic ETHBTC

`SYN_ETHBTC` is calculated from `ETHUSDC` and `BTCUSDC`.

```text
synthetic_mid = ETHUSDC_mid / BTCUSDC_mid
```

For execution-aware research, bid/ask math must be used instead of mid-only math:

```text
synthetic_bid = ETHUSDC_bid / BTCUSDC_ask
synthetic_ask = ETHUSDC_ask / BTCUSDC_bid
synthetic_spread = synthetic_ask - synthetic_bid
```

This captures the cost of buying or selling ETH while hedging through BTC. Mid-only synthetic series are useful for rough visualization, but they overstate executable edge.

## Data Collection Policy

Initial full recording:

- `BTCUSDC` order book snapshots and deltas.
- `BTCUSDC` trades.
- `BTCUSDC` mark price, index price, funding, and open interest when available.
- `ETHUSDC` order book snapshots and deltas.
- `ETHUSDC` trades.
- `ETHUSDC` mark price, index price, funding, and open interest when available.

Initial derived recording:

- `SYN_ETHBTC` mid, bid, ask, spread, and returns.
- Leg timestamps and receive timestamps.
- Leg staleness and timestamp skew.
- Synthetic spread cost.
- Relative volatility and ETH beta to BTC.

Initial ETHBTC policy:

- Direct `ETHBTC` data is disabled by default.
- Full-depth `ETHBTC` downloads are not required for the MVP.
- A future lightweight reference feed may collect direct `ETHBTC` top-of-book or candles only for benchmarking direct-vs-synthetic behavior.

## Staleness Rules

`SYN_ETHBTC` must be marked stale or unavailable when either leg is stale. At minimum the derived record should include:

- `ethusdc_source_timestamp`.
- `btcusdc_source_timestamp`.
- `ethusdc_receive_timestamp`.
- `btcusdc_receive_timestamp`.
- `leg_timestamp_skew_ms`.
- `is_stale`.
- `stale_reason`.

Strategy, model, paper, and order-preview workflows must reject relative-value decisions when the synthetic series is stale or when fee data is stale.

## Relative-Value Expression

The strategy layer may later express ETH/BTC relative value through a parent intent:

```text
Parent: trade ETH/BTC relative value
Children:
  - ETHUSDC maker-first order intent
  - BTCUSDC maker-first hedge order intent
```

The execution engine must never submit `SYN_ETHBTC`; it is not a venue symbol. If one child leg fills and the other does not, risk and portfolio services must manage leg imbalance explicitly.

## Risk Requirements

Relative-value workflows must track:

- ETH notional.
- BTC notional.
- Gross exposure.
- Net USDC exposure.
- ETH beta to BTC.
- Hedge ratio.
- Leg imbalance.
- Synthetic spread cost.
- Funding differential.
- Liquidation buffer.
- Expected edge after costs.

No relative-value strategy session may run unless the fee model is current and `expected_edge_after_costs` includes both executable legs.

## Promotion Criteria For Direct ETHBTC

Direct `ETHBTC` can be reconsidered only after:

- Dynamic symbol metadata and filters are validated.
- Dynamic maker and taker fees are available and audited.
- Direct order book quality is measured against synthetic order book quality.
- Paper trading supports direct and synthetic relative-value comparisons.
- Portfolio accounting handles the instrument without confusing it with synthetic exposure.
- Risk tests prove direct `ETHBTC` cannot bypass two-leg exposure controls.
- Review explicitly changes `ETHBTC` from reference-only to executable.

Until then, `ETHBTC` remains reference-only and disabled by default.
