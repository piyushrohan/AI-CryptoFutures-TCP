# Phase 3-6 Implementation Status

This document records the deterministic local MVP implementation for roadmap
phases 3 through 6.

The implementation remains paper-only. It does not add Binance connectivity,
Binance connector logic, real API keys, live trading, testnet trading, model
trading, or production strategy alpha.

## Phase 3: Paper Trading Control Loop

Implemented:

- Paper order lifecycle schemas for intent, preview, expected edge, fill,
  order, reconciliation, and portfolio exposure.
- In-memory paper exchange with deterministic local fills.
- Maker-first validation with post-only and `GTX` requirements.
- Taker behavior rejected unless an explicit paper taker gate is enabled.
- Dynamic local fee policy included in `expected_edge_after_costs`.
- Independent hedge-mode `LONG` and `SHORT` book updates.
- Paper reset, cancel record, panic halt, panic cancel, and panic flatten
  scaffolding.
- API endpoints for paper preview, submit, portfolio, orders, reconciliation,
  reset, and paper panic actions.
- Frontend paper control surface for preview, submit, exposure, and result
  inspection.

Still out of scope:

- Binance testnet or live exchange submission.
- Production matching engine behavior.
- Persistent paper portfolio storage.

## Phase 4: Portfolio and Risk Foundation

Implemented:

- Portfolio exposure calculations for gross exposure, net exposure, long
  exposure, short exposure, hedge ratio, liquidation buffer, and funding
  exposure.
- Paper risk gates for max account leverage, max symbol exposure, max portfolio
  gross exposure, daily loss, drawdown, liquidation buffer, stale data, API
  error halt, abnormal spread, funding spike, volatility halt, order spam
  protection, and panic halt.
- Risk checks remain independent from strategy logic.
- Missing stale or unsafe inputs veto paper order submission.

Still out of scope:

- Production-grade cross-margin or Portfolio Margin accounting.
- Real exchange reconciliation.
- Live or testnet risk enforcement.

## Phase 5: Microstructure Research and Backtesting

Implemented:

- Synthetic in-repo BTCUSDC and ETHUSDC market-depth fixtures.
- `SYN_ETHBTC` derivation from `ETHUSDC / BTCUSDC`.
- Feature generation for order book imbalance, microprice, spread, depth slope,
  queue imbalance, trade aggression, short-horizon returns, realized
  volatility, funding rate, open interest, liquidation notional,
  latency-adjusted returns, synthetic spread cost, and leg timestamp skew.
- Deterministic local backtest report with maker/taker ratio, fill ratio,
  fees, adverse-selection estimate, missed fills, latency, and
  `expected_edge_after_costs`.
- API and frontend inspection surfaces for research features and backtest
  report.

Still out of scope:

- Downloaded market data.
- Direct ETHBTC executable trading.
- Historical production replay infrastructure.

## Phase 6: Strategy Sessions in Paper Mode

Implemented:

- Paper-only strategy session manager.
- Start, pause, stop, status, and recommendation inspection.
- Maker-first microstructure session family scaffold.
- No-trade recommendation records by default.
- Session-level maker/taker leakage metric.
- Explicit notes that strategy alpha is not implemented.

Still out of scope:

- Real alpha strategy logic.
- AI/model-driven order intents.
- Any direct strategy access to exchange connectors.
- Testnet auto-trade or live trading.

## Validation

The implementation is covered by deterministic unit tests for:

- Paper order preview and submit.
- Maker-first post-only rejection.
- Taker behavior gates.
- Independent hedge-mode `LONG` and `SHORT` books.
- Stale data and exposure vetoes.
- Panic halt and flatten paper behavior.
- Synthetic `SYN_ETHBTC` derivation.
- Replay and backtest determinism.
- Paper strategy session start, pause, stop, and no-trade behavior.
- API payload behavior for phase 3-6 surfaces.
