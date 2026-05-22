# Fee and Symbol Policy

The initial preferred strategy universe is Binance USDⓈ-M Futures perpetual pairs quoted in USDC, such as `BTCUSDC` and `ETHUSDC`, when maker-fee economics are favorable.

This preference is not a hard-coded trading rule. It is a research and platform policy that must be validated dynamically through symbol metadata, fee schedules, liquidity, funding, and execution quality.

For the initial BTC/ETH focus, `BTCUSDC` and `ETHUSDC` are the only executable instruments. `SYN_ETHBTC` is a derived, non-executable series calculated from `ETHUSDC / BTCUSDC`. Direct `ETHBTC` is reference-only and disabled by default unless a future policy change promotes it after fee, liquidity, portfolio, and risk validation.

## USDC-quoted Pair Preference

USDC-quoted perpetual pairs are preferred initially because they may offer attractive maker-fee economics during certain venue promotions or account tiers. The platform should still evaluate each symbol before allowing a strategy session or trading workflow.

Symbol eligibility should consider:

- Contract status.
- Quote asset.
- Margin asset.
- Tick size.
- Lot size.
- Min notional.
- Available order types.
- Time-in-force support.
- Recent spread and depth.
- Expected fill probability.
- Funding behavior.
- Dynamic maker and taker fees.

## Three-Asset BTC/ETH Policy

The initial focused universe is defined in [Three-Asset BTC/ETH Universe](../market_data/three_asset_universe.md) and `configs/symbol_universe.yml`.

Initial roles:

- `BTCUSDC`: executable, full data recording.
- `ETHUSDC`: executable, full data recording.
- `SYN_ETHBTC`: derived, non-executable, calculated from `ETHUSDC / BTCUSDC`.
- `ETHBTC`: direct reference-only instrument, disabled by default.

Full `ETHBTC` order book downloads are not required for the MVP because the first relative-value implementation should prove the two-leg USDC execution path. Direct `ETHBTC` may be used later as a lightweight benchmark or promoted only after explicit review.

## Dynamic Fees

Maker and taker fees must be dynamic, configurable, audited, and included in expected-edge calculations.

Future implementation should support fee sources such as:

- Binance [user commission rate](https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/User-Commission-Rate) endpoint.
- Account tier configuration.
- Symbol-specific overrides.
- Time-bounded promotional fee policies.
- Manual research assumptions for paper and backtest workflows.

The active fee assumption must be visible in the frontend and stored in audit records for trading decisions, model decisions, paper fills, backtests, and evaluations.

Phase 2 exposes a local configurable fee-policy inspector for `BTCUSDC` and `ETHUSDC`. The values are local development assumptions, source-labeled, timestamped, and validated for freshness. They are not Binance account commission data and must not be used for live or testnet execution.

## No Permanent Zero-fee Assumption

Fee promotions must not be assumed permanent. The system must not hard-code permanent zero maker fees for USDC pairs or any other venue universe.

If a maker fee is configured as zero for a research window or promotion, the configuration must include:

- Symbol or symbol universe.
- Source of the assumption.
- Effective start time.
- Effective end time or review time.
- Approval record.
- Fallback fee when the promotion expires or cannot be verified.

## expected_edge_after_costs

Every trading decision that depends on expected edge must include an `expected_edge_after_costs` calculation before order submission or recommendation approval.

At minimum:

```text
expected_edge_after_costs =
  expected_gross_edge
  - expected_maker_or_taker_fee
  - expected_spread_cost_or_capture_adjustment
  - expected_slippage
  - expected_adverse_selection
  - expected_funding_cost
  - expected_latency_cost
```

The exact model may evolve, but costs must not be ignored.

## Audit Requirements

Audit records should include:

- Fee source.
- Maker fee assumption.
- Taker fee assumption.
- Promotion metadata when applicable.
- Expected gross edge.
- Expected costs.
- `expected_edge_after_costs`.
- Decision to trade or not trade.

No-trade decisions are important and should be captured for model evaluation.
