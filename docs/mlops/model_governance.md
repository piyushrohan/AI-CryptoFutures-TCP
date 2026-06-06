# Model Governance

Models must be governed as deployable artifacts with traceable data, features, evaluations, approvals, and decisions.

## Governance Requirements

- Model registry: every candidate model must have an identifier, version, metadata, owner, and approval state.
- Feature versioning: features must be reproducible by version and tied to source data windows.
- Training data windows: training, validation, and test windows must be explicit and recorded.
- Backtest approval: a model must pass documented backtest criteria before paper evaluation.
- Paper approval: a model must pass paper-trading evaluation before internal Binance testnet validation, `LIVE` read-only validation, or live-trade consideration.
- Human approval before live deployment: live use requires explicit human approval and configuration gates.
- Model decision records: model outputs must be recorded with inputs, feature versions, model version, timestamp, confidence, and resulting action or non-action.
- Explainability requirement: model-assisted decisions must be explainable enough for operators to understand why a recommendation or command was produced.
- Expected-edge requirement: model-assisted decisions must include dynamic fee assumptions and expected edge after costs when recommending a trading action or no-trade decision.
- Microstructure research: scalping models should support features such as order book imbalance, microprice, spread, depth, trade aggression, fill probability, adverse selection, and latency-adjusted returns.

## Deployment Posture

No model should be able to bypass command validation, risk checks, portfolio checks, execution checks, audit, reconciliation, or live-trading gates. MLOps approval states can describe readiness, but they must never authorize execution on their own. Models and strategies must never directly call the exchange connector.

## Current Local Implementation

The Phase 7 local implementation adds model registry metadata, feature-version metadata, evaluation summaries, `ModelDecisionRecord` payloads, and recommendation previews. A recommendation preview is accepted only when a complete decision record exists. Acceptance is still not order approval; it only means the recommendation is explainable enough to enter the normal command, risk, portfolio, execution, audit, and reconciliation path.
