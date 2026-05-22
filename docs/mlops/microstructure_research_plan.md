# Microstructure Research Plan

AI-CryptoFutures-TCP should support market microstructure research for short-horizon, maker-first crypto futures workflows. The first venue family is Binance USDⓈ-M Futures, with a preferred initial research universe of USDC-quoted perpetual pairs such as `BTCUSDC` and `ETHUSDC` when maker-fee economics are favorable.

This plan defines research features and targets. It does not implement strategy code.

The first BTC/ETH relative-value research path should use `BTCUSDC` and `ETHUSDC` as executable instruments and compute `SYN_ETHBTC = ETHUSDC / BTCUSDC` as a derived, non-executable series. Direct `ETHBTC` is reference-only and disabled by default unless a future policy change promotes it.

## Research Objectives

The research stack should help answer:

- Is there positive expected edge after dynamic fees and execution costs?
- When should the system post liquidity?
- When should the system avoid trading?
- How often does maker intent leak into taker fills?
- What fill probability is realistic at a given price level?
- How much adverse selection follows fills?
- How sensitive are results to latency?

## Feature Families

### Order Book Imbalance

Order book imbalance measures bid and ask pressure across one or more depth levels.

Potential features:

- Best-level imbalance.
- Multi-level depth imbalance.
- Distance-weighted imbalance.
- Imbalance change rate.
- Imbalance persistence.

### Microprice

Microprice estimates a fair price adjusted by top-of-book size imbalance.

Potential features:

- Microprice minus midprice.
- Microprice return.
- Microprice slope.
- Microprice divergence from mark price.

### Spread and Depth

Spread and depth features describe liquidity and expected spread capture.

Potential features:

- Quoted spread.
- Effective spread.
- Depth at best bid and ask.
- Depth within configured basis-point bands.
- Spread regime classification.

### Synthetic ETH/BTC

Synthetic ETH/BTC features should be computed from time-aligned `ETHUSDC` and `BTCUSDC` books.

Potential features:

- `SYN_ETHBTC` mid, bid, ask, and spread.
- Direct-vs-synthetic basis when direct `ETHBTC` reference data is enabled.
- Leg timestamp skew.
- Leg staleness flags.
- ETH beta to BTC.
- Synthetic spread cost.
- Funding differential between executable legs.

### Trade Aggression

Trade aggression estimates whether recent trades are lifting offers or hitting bids.

Potential features:

- Buyer-initiated notional.
- Seller-initiated notional.
- Trade sign imbalance.
- Aggressive trade burst indicators.
- Large trade flags.

### Volatility Regime

Volatility affects fill probability, adverse selection, and quote lifetime.

Potential features:

- Short-horizon realized volatility.
- Volatility regime buckets.
- Mark-price volatility.
- Spread-adjusted volatility.
- Volatility acceleration.

### Latency

Latency-aware features are required because stale decisions can look profitable in research while failing in execution.

Potential features:

- Market data receive delay.
- Feature computation delay.
- Decision delay.
- Submission delay.
- Cancel delay.
- Reconciliation delay.

## Model Targets

### Short-horizon Returns

Predict returns over short horizons relevant to scalping and maker inventory risk. Horizons should be explicit and versioned.

Targets may include:

- Midprice return.
- Microprice return.
- Mark-price return.
- Latency-adjusted return.
- Post-fill return.

### Fill Probability

Predict whether a maker order at a selected price level fills within a configured horizon.

Labels should account for queue approximation, partial fills, cancellations, and stale order book state.

### Adverse Selection

Predict whether a fill is followed by unfavorable price movement after fees and spread capture.

Adverse-selection targets should be measured at multiple horizons and by side.

### Expected Holding Period

Predict how long a position or quote is likely to remain open. This is needed for funding exposure, inventory risk, and capital allocation.

### No-trade Decisions

No-trade is a first-class decision. Models should be rewarded for avoiding low-quality trades when expected edge after costs is negative or uncertain.

No-trade labels and decision records should capture the reason, such as low fill probability, adverse selection risk, stale data, insufficient edge, fee uncertainty, or risk veto.

## Evaluation Requirements

Research results should report:

- Expected edge before costs.
- Expected edge after costs.
- Maker fill rate.
- Taker leakage rate.
- Realized spread capture.
- Adverse-selection cost.
- Fee impact.
- Funding impact.
- Latency-adjusted returns.
- Drawdown.
- Symbol-level and portfolio-level exposure.

Backtests must use dynamic fee assumptions and must not assume permanent zero maker fees.

## Deployment Boundary

Research outputs and model predictions are recommendations, not direct orders. Models must produce decision records and enter the same frontend, backend validation, risk, portfolio, execution, audit, and reconciliation lifecycle as manual orders.
