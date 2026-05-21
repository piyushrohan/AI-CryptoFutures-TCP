# Autonomy Ladder

The autonomy ladder defines how AI-CryptoFutures-TCP may move from observation to increasingly automated trading workflows. Each stage requires explicit approval, risk gates, tests, auditability, and operator visibility.

Live trading remains disabled by default.

## Core Rules

- No stage can bypass risk checks.
- No stage can bypass portfolio checks.
- No stage can bypass execution checks.
- No stage can bypass audit records.
- No stage allows the browser to receive secrets or sign exchange requests.
- No stage allows a strategy or model to directly call the exchange connector.
- Advancing a stage requires explicit human approval.
- Downgrading a stage must be fast and operator-controlled.

## Stage 0: Observe Only

The platform displays market, portfolio, risk, audit, and model state. It does not create order intents.

Required gates:

- Observe mode active.
- Live trading disabled.
- Read-only or simulated data paths only.

## Stage 1: Suggest Only

Models or strategies may produce recommendations and decision records. The system does not submit order intents from those recommendations.

Required gates:

- Model decision records.
- Explainability output.
- No direct exchange connector access.
- Frontend review.

## Stage 2: Human Approval Required

The frontend displays recommendations and allows an operator to approve or reject an order intent. Approved intents still pass risk, portfolio, execution, and audit checks.

Required gates:

- Operator approval.
- Risk approval.
- Portfolio approval.
- Execution approval.
- Audit record.

## Stage 3: Paper Auto-trade

Approved strategy or model sessions may automatically submit paper order intents to the paper exchange.

Required gates:

- Paper mode.
- Paper exchange only.
- Risk and portfolio checks.
- Deterministic test scenarios.
- Taker leakage monitoring.
- Session-level stop controls.

## Stage 4: Testnet Auto-trade

Approved sessions may automatically submit order intents to Binance USDⓈ-M Futures testnet through backend-only signing.

Required gates:

- Testnet mode.
- Testnet credentials only.
- Backend-only exchange signing.
- Binance symbol filter validation.
- Maker/taker policy validation.
- User data stream reconciliation.
- Rate-limit monitoring.
- Operator-visible halt controls.

## Stage 5: Tiny Live With Approval

Tiny live orders may be submitted only after explicit per-action human approval and all live-trading gates pass.

Required gates:

- `live-trade` mode explicitly enabled.
- Live trading explicitly enabled.
- Per-action human approval.
- Tiny notional limits.
- Restricted API keys.
- Withdrawals disabled.
- Risk, portfolio, execution, audit, and notification services healthy.
- Dynamic fees and expected edge after costs recorded.

## Stage 6: Tiny Live Autonomous

Tiny live autonomous trading may submit orders without per-action approval, but only within strict notional, symbol, time, risk, and execution limits.

Required gates:

- Dedicated approval for this autonomy stage.
- Tiny notional and daily loss limits.
- Maker-first default.
- Explicit taker leakage cap.
- Automatic halt on stale data, API errors, reconciliation drift, or risk breaches.
- Continuous audit and frontend visibility.

## Stage 7: Scaled Live Autonomous

Scaled live autonomous trading is the most mature stage and should be considered only after extensive evidence from paper, testnet, tiny live with approval, and tiny live autonomous stages.

Required gates:

- Independent approval.
- Scaled risk limits.
- Multi-symbol portfolio controls.
- Cross-margin-aware exposure checks.
- Funding and liquidation-buffer checks.
- Operational runbooks.
- Monitoring and alerting.
- Incident response process.
- Rollback and kill-switch drills.

## Advancement Criteria

Moving up the autonomy ladder should require:

- Documented approval.
- Passing tests.
- Clean audit history.
- Stable reconciliation.
- Acceptable drawdown and error profile.
- Explainable model decisions.
- Dynamic fee and cost accounting.
- Demonstrated operator controls.

Failure at any stage should allow immediate downgrade to a safer stage.
