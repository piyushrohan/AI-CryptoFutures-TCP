# Frontend Control Surface

The frontend is the primary control tower for AI-CryptoFutures-TCP. It should eventually allow the operator to control observe, paper, testnet, live-readonly, live-trade approval, training, evaluation, backtesting, strategy sessions, and model deployment without bypassing backend validation.

The frontend sends intent. Backend services validate, risk-check, portfolio-check, execute, audit, and reconcile that intent.

## Control Surface Rules

- The browser must never receive exchange secrets.
- The browser must never sign Binance requests.
- Every action must resolve to an authenticated backend command.
- Every command must have an audit trail.
- Trading actions must pass risk, portfolio, and execution checks.
- Strategies and models must never directly call the exchange connector.
- Live trading must remain disabled by default and require explicit approval gates.

## Screen-to-command Map

| Frontend screen | Operator actions | Backend command family | Required backend checks |
| --- | --- | --- | --- |
| Overview dashboard | Select mode, inspect venue health, inspect risk state, inspect portfolio state | `GetSystemStatus`, `GetModeStatus`, `GetRiskState`, `GetPortfolioSnapshot` | Auth, authorization, stale-state labeling |
| Manual trading | Draft order intent, preview costs, submit paper/testnet/live-gated order, cancel order | `CreateOrderIntent`, `PreviewOrder`, `SubmitOrderIntent`, `CancelOrderIntent` | Auth, mode, schema, symbol filters, fee model, risk, portfolio, execution, audit |
| Paper trading | Start paper session, submit paper orders, reset paper state, inspect simulated fills | `CreatePaperSession`, `SubmitPaperOrder`, `ResetPaperPortfolio`, `GetPaperReconciliation` | Auth, paper mode, risk, portfolio, paper exchange, audit |
| Testnet trading | Enable testnet session, submit approved testnet orders, reconcile order state | `CreateTestnetSession`, `SubmitTestnetOrder`, `GetTestnetReconciliation` | Auth, testnet mode, backend-only signing, Binance filters, risk, portfolio, execution, audit |
| Live-readonly | Inspect live balances, positions, orders, margin, liquidation estimates | `GetLiveReadonlyAccount`, `GetLiveReadonlyPositions`, `GetLiveReadonlyOrders` | Auth, live-readonly permission, read-only credentials, secrets isolation, audit |
| Live-trade approval | Request live gate status, approve live session, approve tiny live action, halt live session | `RequestLiveApproval`, `ApproveLiveGate`, `ApproveLiveOrderIntent`, `DisableLiveTrading` | Auth, elevated permission, live gates, risk health, portfolio health, audit |
| Training | Configure training window, launch training job, inspect metrics, compare candidates | `CreateTrainingJob`, `CancelTrainingJob`, `GetTrainingRun`, `CompareTrainingRuns` | Auth, data version, feature version, object storage, model registry, audit |
| Evaluation | Run model evaluation, compare metrics, inspect decision quality, approve evaluation stage | `CreateEvaluationJob`, `GetEvaluationReport`, `ApproveEvaluationStage` | Auth, data windows, model registry, metrics storage, audit |
| Backtesting | Configure backtest, launch run, inspect fills, inspect costs, compare scenarios | `CreateBacktestJob`, `CancelBacktestJob`, `GetBacktestReport` | Auth, data version, fee model, slippage model, deterministic config, audit |
| Strategy sessions | Start paper strategy session, pause session, inspect recommendations, stop session | `CreateStrategySession`, `PauseStrategySession`, `StopStrategySession`, `GetStrategyRecommendations` | Auth, mode, risk profile, model policy, audit |
| Model registry | Register candidate, inspect lineage, approve stage, deploy to serving mode | `RegisterModelCandidate`, `ApproveModelStage`, `DeployModelVersion`, `DisableModelVersion` | Auth, registry policy, approval gates, audit |
| Panic controls | Halt new orders, cancel open orders, disable strategy sessions, disable live trading | `ActivatePanicHalt`, `CancelOpenOrders`, `DisableAutomation`, `DisableLiveTrading` | Auth, elevated permission, audit, risk-state propagation |
| Audit viewer | Search commands, decisions, approvals, vetoes, order lifecycle events | `SearchAuditRecords`, `GetAuditRecord`, `ExportAuditBundle` | Auth, authorization, immutable audit access |
| Model decision inspector | Inspect model decision record, explanation, features, confidence, recommendation, cost assumptions | `GetModelDecisionRecord`, `ExplainModelDecision`, `GetDecisionCostBreakdown` | Auth, model registry, feature metadata, audit |

## Manual Trading

Manual trading should feel direct in the frontend, but it is still a backend-controlled workflow. The operator drafts intent, previews expected costs and risk impact, confirms the order, and receives a backend decision.

Manual orders must pass:

- Command validation.
- Symbol and venue metadata validation.
- Dynamic fee and expected-edge checks when relevant.
- Risk checks.
- Portfolio exposure and margin checks.
- Maker-first execution checks by default.
- Audit recording.
- Reconciliation.

## AI-assisted Trading

The frontend may display model recommendations, but recommendations are not orders. AI-assisted actions should expose the decision record, feature version, model version, confidence, expected edge after costs, no-trade reason when applicable, and operator approval state.

If the operator accepts a recommendation, the frontend submits an order intent to the backend. The model service never calls the exchange connector directly.

## Training, Evaluation, Backtesting, and Deployment

The frontend should eventually coordinate the complete model lifecycle:

1. Select data windows and feature versions.
2. Launch training jobs.
3. Launch evaluations and backtests.
4. Compare metrics and reports.
5. Promote model candidates through approval stages.
6. Deploy approved model versions to serving contexts.
7. Disable or roll back model versions.

Model deployment changes must be audited. Deployment does not grant live-trading permission.

## Panic Controls

Panic controls must be visible, fast, and auditable. They should allow privileged operators to halt new trading intent, disable automation, cancel eligible open orders, disable live trading, and force the platform into a safer mode.

Panic actions should be backend commands with strong authorization, audit records, notification events, and immediate frontend state updates.
