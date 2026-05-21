# Margin and Exposure Model

The portfolio engine should evolve toward cross-margin-aware accounting for multi-symbol Binance USDⓈ-M Futures workflows. This document defines the target model for exposure, margin, hedge ratio, beta exposure, funding exposure, liquidation buffer, and capital allocation.

This is a design document only. It does not implement portfolio logic.

## Accounting Scope

The portfolio engine should support:

- Paper portfolios.
- Testnet portfolios.
- Live-readonly portfolios.
- Future live-trade portfolios.
- Multi-symbol exposure.
- Hedge-mode independent `LONG` and `SHORT` books.
- Cross-margin-aware calculations when account mode and venue data support them.

Portfolio state must be reconciled against the selected venue or paper exchange before risk or execution decisions depend on it.

## Gross Exposure

Gross exposure is the sum of absolute notional exposure across books.

Gross exposure should be tracked by:

- Symbol.
- Side.
- Strategy session.
- Model version when applicable.
- Venue.
- Portfolio.

Risk limits should be able to cap gross exposure even when net exposure appears small.

## Net Exposure

Net exposure is directional exposure after offsetting long and short notional where the portfolio model permits it.

Net exposure is useful for directional risk, but it must not replace side-specific hedge-mode books when margin, liquidation, reduce-only behavior, or realized PnL depend on side.

## Hedge Ratio

Hedge ratio measures how much exposure is offset by opposite exposure. It may be computed at symbol, basket, or portfolio level.

The platform should make clear whether hedge ratio is:

- Same-symbol long/short offset.
- Cross-symbol offset.
- Beta-adjusted offset.
- Strategy-defined hedge.

Hedge ratio should not imply risk-free exposure.

## Beta Exposure

Beta exposure estimates portfolio sensitivity to a reference asset, index, or basket. For crypto futures, examples may include BTC beta, ETH beta, or a custom crypto market factor.

Beta exposure should be versioned with the estimation method, lookback window, and data source.

## Symbol Exposure

Symbol exposure should include:

- Long notional.
- Short notional.
- Gross notional.
- Net notional.
- Open-order notional.
- Pending reduce-only notional.
- Margin contribution.
- Funding contribution.

Symbol exposure should support future per-symbol risk limits and frontend drill-down.

## Sector Exposure

Sector exposure groups symbols by configured taxonomy, such as majors, layer 1, DeFi, exchange tokens, memecoins, or custom research baskets.

Sector taxonomy must be configurable and audited when used for risk limits.

## Funding Exposure

Funding exposure tracks expected and realized funding impact by symbol, side, venue, and holding period.

Funding should be included in expected-edge calculations for strategy sessions, backtests, model decisions, and order previews when the intended holding period crosses funding windows.

## Liquidation Buffer

Liquidation buffer measures distance from estimated liquidation conditions. It should be calculated using venue-provided account data where available and conservative approximations otherwise.

Liquidation-buffer checks should include:

- Current mark price.
- Side-specific position state.
- Margin mode.
- Leverage.
- Maintenance margin assumptions.
- Open orders and pending exposure.
- Cross-margin interactions where applicable.
- Stale data status.

When liquidation inputs are stale or unavailable, risk should fail closed.

## Multi-symbol Capital Allocation

The portfolio engine should support allocation across symbols, strategies, and model sessions.

Capital allocation should account for:

- Available margin.
- Gross and net exposure.
- Correlation or beta exposure.
- Funding exposure.
- Liquidity.
- Expected edge after costs.
- Drawdown limits.
- Daily loss limits.
- Open-order commitments.

Allocation decisions should be explainable from the frontend and auditable in backend records.

## Cross-margin Awareness

Cross-margin behavior can make one symbol's losses affect available margin for other symbols. The platform should not treat symbols as isolated when the account mode creates shared collateral risk.

Future cross-margin-aware checks should include portfolio-level stress, concentration limits, liquidation buffer, and funding liability across all active symbols.
