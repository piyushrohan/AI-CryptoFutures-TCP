# Model Governance

Models must be governed as deployable artifacts with traceable data, features, evaluations, approvals, and decisions.

## Governance Requirements

- Model registry: every candidate model must have an identifier, version, metadata, owner, and approval state.
- Feature versioning: features must be reproducible by version and tied to source data windows.
- Training data windows: training, validation, and test windows must be explicit and recorded.
- Backtest approval: a model must pass documented backtest criteria before paper evaluation.
- Paper approval: a model must pass paper-trading evaluation before any live-readonly or live-trade consideration.
- Human approval before live deployment: live use requires explicit human approval and configuration gates.
- Model decision records: model outputs must be recorded with inputs, feature versions, model version, timestamp, confidence, and resulting action or non-action.
- Explainability requirement: model-assisted decisions must be explainable enough for operators to understand why a recommendation or command was produced.

## Deployment Posture

No model should be able to bypass command validation, risk checks, portfolio checks, execution checks, or live-trading gates.
