# Maker Microstructure Execution

Execution should be maker-first by default. The platform should prefer liquidity-providing behavior unless an operator, strategy policy, risk profile, and execution gate explicitly allow taker behavior.

Maker-first does not mean blindly placing passive orders. It means modeling whether posting liquidity has positive expected edge after fees, fill probability, adverse selection, latency, and cancellation risk.

## Maker-first Policy

Default order intent should be:

- Limit-style.
- Post-only where the venue supports it.
- Cancel-if-crossing.
- Fee-aware.
- Spread-aware.
- Queue-aware.
- Audited.

Market orders and other taker-capable behavior must be explicit, gated, tested, and audited.

## Post-only Intent

Post-only intent should be represented as a first-class internal field, not inferred from a raw venue flag.

The execution engine should translate post-only intent to the venue-specific payload, such as Binance USDⓈ-M `GTX` time-in-force where supported and verified.

If a post-only order would cross the book, the default behavior should be reject or cancel before submission. The system must not silently become taker.

## Cancel-if-crossing

Before submission, maker-first execution should compare the intended price against a fresh order book snapshot.

If the order would immediately take liquidity, execution should:

- Reject the intent.
- Cancel and reprice according to an explicit policy.
- Or proceed only if taker gates allow it.

The selected behavior must be configured, tested, and audited.

## Max Taker Leakage

Some strategies may tolerate limited taker leakage due to race conditions, queue movement, or venue behavior. Any tolerance must be explicit.

The platform should track:

- Taker fills as a percentage of total fills.
- Taker notional.
- Taker fee impact.
- Taker leakage by symbol, strategy, model, and session.
- Breaches of configured max taker leakage.

Breaches should trigger alerts, audit events, and possible strategy-session halt.

## Queue Position Approximation

The execution engine should estimate queue position using available market data:

- Order book depth at target price.
- Recent trades through the level.
- Order book updates after placement.
- Own order quantity.
- Time priority approximation.
- Cancellation rate around the level.

Queue estimates are approximations, not guarantees. They should be marked as such in frontend displays and model features.

## Fill Probability

Maker-first decisions should estimate fill probability over the intended holding or quote horizon.

Inputs may include:

- Distance from midprice.
- Queue depth ahead.
- Trade aggression.
- Short-horizon volatility.
- Spread regime.
- Time of day.
- Symbol liquidity.
- Recent cancel/replace behavior.

Low fill probability can turn apparent spread capture into no-trade.

## Adverse Selection

Posting liquidity can be costly when fills occur just before price moves against the position. The platform should measure and model adverse selection through post-fill returns, order book imbalance, microprice, trade aggression, and latency-adjusted price movement.

Execution decisions should include adverse-selection estimates in expected-edge calculations.

## Latency

Latency affects both maker placement and cancellation quality. Execution and research should track:

- Market data receive latency.
- Decision latency.
- Order submission latency.
- Exchange acknowledgement latency.
- Cancel latency.
- User data stream reconciliation latency.

Latency-adjusted returns should be used in research and model evaluation.

## Spread Capture

Spread capture should be measured after fees, adverse selection, failed fills, and inventory effects. A quoted spread is not realized edge.

The platform should distinguish:

- Quoted spread.
- Expected spread capture.
- Realized spread capture.
- Spread capture after fees.
- Spread capture after adverse-selection adjustment.

## Cancel/replace Discipline

Cancel/replace behavior must be rate-limit-aware and audited. Excessive churn can create rate-limit pressure, queue loss, execution noise, and operational risk.

Policies should define:

- Minimum quote lifetime.
- Max cancel/replace rate.
- Max open orders.
- Reprice threshold.
- Stale quote timeout.
- Queue abandonment conditions.
- Panic cancel behavior.

Cancel/replace decisions should be visible in audit and execution analytics.
