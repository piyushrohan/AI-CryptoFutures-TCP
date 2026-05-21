# System Design Document

## 1. Mission

AI-CryptoFutures-TCP is a private, frontend-first Trading Control Platform for AI-assisted crypto futures operations. The first target venue is Binance USDⓈ-M Futures, with paper trading and Binance testnet workflows preceding any live capability.

The preferred initial strategy universe is USDC-quoted Binance USDⓈ-M Futures perpetual pairs, such as `BTCUSDC` and `ETHUSDC`, subject to current dynamic fee, liquidity, funding, and risk policy.

The platform mission is to give an operator a control tower for market observation, manual order intent creation, model decision review, paper execution, testnet execution, portfolio supervision, risk enforcement, auditability, training, evaluation, backtesting, strategy sessions, model deployment, and future gated live trading.

This is not a simple bot. The system is designed as a governed trading platform where the frontend is the primary human control surface, backend services validate all commands, independent risk controls can veto any action, and exchange secrets remain isolated from the browser.

## 2. Non-goals

The initial architecture does not aim to implement trading strategy logic, connect to live Binance accounts, or provide live trading by default.

The system does not optimize for fully autonomous trading. Automation may assist decisions, propose orders, or operate in approved simulation modes, but command validation, risk checks, portfolio checks, execution checks, audit records, and human-operable controls remain first-class platform requirements.

The browser must never sign Binance requests, hold exchange credentials, or directly call authenticated exchange endpoints.

The platform is not intended to support withdrawals, custody operations, unmanaged secrets, opaque model decisions, or strategy-specific risk shortcuts.

## 3. Operator Mode, Venue Target, Gates, and Lanes

The frontend should expose only two primary operator modes:

- `PAPER`: the first full user-facing mode.
- `LIVE`: introduced later, initially as read-only.

The backend must keep more precise internal state. The simple two-mode UI must not hide, weaken, or bypass live gates, risk checks, portfolio checks, execution checks, MLOps approval states, audit, or reconciliation.

### operator_mode

- `paper`: safe operator-facing mode for internal paper workflows and later internal testnet validation lanes.
- `live`: operator-facing live account context, introduced first with read-only credentials.

### venue_target

- `internal_paper`: internal simulator and first full execution target.
- `binance_testnet`: internal Binance USDⓈ-M Futures validation lane, not a top-level operator mode.
- `binance_live`: live Binance USDⓈ-M Futures account target.

### credential_scope

- `none`: no exchange credentials required.
- `read_only`: live account inspection only.
- `trading`: trading-capable credentials, usable only behind explicit gates.

### trading_gate

- `locked`: trading unavailable.
- `approval_required`: trading unavailable until explicit human approval.
- `tiny_live`: tiny live research limits only.
- `armed`: live trading gate armed for an approved workflow.
- `halted`: trading blocked by operator or system halt.

### autonomy_stage

- `observe_only`
- `suggest_only`
- `human_approval`
- `paper_auto`
- `testnet_auto`
- `tiny_live_auto`
- `scaled_live_auto`

Observe is an autonomy stage or session state, not a top-level operator mode.

### mlops_approval_state

- `research_candidate`
- `backtest_approved`
- `paper_approved`
- `testnet_validated`
- `live_readonly_validated`
- `live_trade_candidate`
- `live_trade_approved`

MLOps approval can describe model or strategy readiness, but it must never bypass risk gates, live gates, portfolio checks, execution checks, audit, or reconciliation.

### Examples

Safe default config:

```yaml
operator_mode: paper
venue_target: internal_paper
credential_scope: none
trading_gate: locked
autonomy_stage: observe_only
mlops_approval_state: research_candidate
live_trading_enabled: false
```

Live read-only config:

```yaml
operator_mode: live
venue_target: binance_live
credential_scope: read_only
trading_gate: locked
autonomy_stage: observe_only
live_trading_enabled: false
```

Binance testnet is an internal validation lane, typically `operator_mode=paper` with `venue_target=binance_testnet`. `LIVE` read-only is `operator_mode=live`, `credential_scope=read_only`, and `trading_gate=locked`. Live-trade capability is `operator_mode=live`, `credential_scope=trading`, and explicit live trading gates.

If any live gate is missing, stale, inconsistent, or disabled, the system must fail closed.

## 4. Core Principle

- Frontend controls everything.
- Backend validates everything.
- Risk engine can veto everything.
- Secrets never touch the frontend.

The frontend is the control tower. It can initiate commands, display state, show model explanations, expose manual controls, and request operator approvals. It cannot bypass backend validation or receive exchange signing material.

The backend is the enforcement boundary. Every command must be authenticated, authorized, schema-validated, mode-checked, audited, risk-checked, portfolio-checked, execution-checked, and reconciled.

The risk engine is independent from strategy logic. A strategy may propose an action; it cannot approve its own risk.

## 5. High-level Architecture

```text
Operator Browser
  -> Web Frontend
  -> API Gateway
  -> Auth / Command Validation / Audit
  -> Market Data / Order Book / Model Service
  -> Strategy Engine
  -> Risk Engine
  -> Portfolio Engine
  -> Execution Engine
  -> Paper Exchange / Binance Testnet / Future Binance Live
  -> Reconciliation
  -> Event Stream
  -> Web Frontend
```

The frontend communicates with the backend through authenticated HTTP APIs and event streams. The backend coordinates domain services through synchronous command APIs for critical paths and asynchronous events for state propagation, reconciliation, monitoring, and audit.

The architecture should support a modular monolith at the beginning and service separation later. Boundaries should be explicit in code and data ownership even before each boundary is deployed as an independent service.

Related design documents:

- [Frontend Control Surface](frontend_control_surface.md) maps operator screens and actions to backend commands.
- [Local Bootstrap](local_bootstrap.md) defines the intended `make up` startup path and safe defaults.
- [Binance USDⓈ-M Constraints](../binance/binance_usdm_constraints.md) captures Binance-specific venue assumptions.
- [Fee and Symbol Policy](../binance/fee_and_symbol_policy.md) defines USDC-quoted pair preference and dynamic fee requirements.
- [Maker Microstructure Execution](../execution/maker_microstructure_execution.md) defines maker-first execution behavior.
- [Margin and Exposure Model](../portfolio/margin_and_exposure_model.md) defines future portfolio accounting.
- [Microstructure Research Plan](../mlops/microstructure_research_plan.md) defines scalping feature and target research.
- [Autonomy Ladder](../risk/autonomy_ladder.md) defines staged autonomy approval gates.
- [Developer Roadmap](../roadmap/developer_roadmap.md) defines phase-gated implementation order.

## 6. Service Boundaries

### web frontend

The web frontend is the operator control tower. It shows market state, order books, account state, portfolio exposure, risk status, model decision records, manual trading controls, `PAPER` and `LIVE` mode indicators, internal lane status, live approval gates, training, evaluation, backtesting, model registry, strategy sessions, panic controls, and audit history.

It must not hold exchange secrets, sign exchange requests, or call authenticated exchange APIs directly.

### API gateway

The API gateway receives frontend commands, authenticates requests, performs coarse authorization, validates request schemas, enforces the operator-mode, venue, credential, trading-gate, autonomy-stage, and MLOps-state tuple, assigns command identifiers, and routes commands to domain services.

It is the first backend enforcement layer, not a pass-through proxy.

### auth service

The auth service owns user identity, sessions, roles, permissions, approval requirements, and operator action authorization.

Future roles should distinguish read-only observation, paper trading, internal testnet validation, live read-only inspection, live-trade approval, panic controls, and administrative configuration.

### market data service

The market data service ingests, normalizes, stores, and publishes market data needed by the frontend, risk engine, portfolio engine, strategy engine, model service, backtests, research workflows, and paper exchange.

It should track source timestamps, receive timestamps, data freshness, symbol metadata, mark prices, index prices, funding rates, and venue health.

### order book service

The order book service maintains normalized order book snapshots and deltas for supported symbols. It should provide frontend displays, liquidity checks, spread and depth measures, order book imbalance, microprice inputs, fill-probability inputs, stale-data detection, and execution pre-checks.

The order book service must expose freshness and sequence integrity so risk and execution components can reject commands when books are stale or inconsistent.

### strategy engine

The strategy engine contains future strategy orchestration and signal generation. It may create recommendations or candidate order intents, but it must not submit orders directly.

Strategy output must be treated as untrusted input to command validation, risk checks, portfolio checks, and execution checks.

### risk engine

The risk engine evaluates whether a command is allowed under configured risk limits, current account state, market conditions, data freshness, operator controls, and platform mode.

It has veto authority over manual and AI-assisted orders.

### portfolio engine

The portfolio engine owns normalized portfolio state: balances, positions, open orders, margin usage, realized PnL, unrealized PnL, exposure, symbol-level books, and portfolio-level aggregates.

It must support future multi-symbol portfolio management, cross-margin-aware exposure, hedge ratio, beta exposure, funding exposure, liquidation-buffer calculations, and hedge-mode-aware position accounting. See [Margin and Exposure Model](../portfolio/margin_and_exposure_model.md).

### execution engine

The execution engine translates approved internal order intents into venue-specific requests, submits them to the selected venue, tracks order state, and reconciles responses.

It must not silently change order aggressiveness, introduce taker orders, alter hedge side, or bypass risk and portfolio approvals. Execution should be maker-first by default; taker behavior must be explicit, gated, tested, and audited. See [Maker Microstructure Execution](../execution/maker_microstructure_execution.md).

### model service

The model service serves approved model versions, produces predictions or recommendations, and writes model decision records.

It must expose explanations, feature versions, model versions, confidence, constraints, expected edge after costs, and the reason for any proposed action or non-action. It must never directly call the exchange connector.

### training worker

The training worker builds candidate models from versioned data windows and feature definitions. It records training metadata, evaluation metrics, artifacts, and lineage.

Training output does not become deployable until it passes governance, evaluation, and approval gates.

### backtest worker

The backtest worker evaluates strategies and model candidates over controlled historical windows. It should use versioned data, deterministic assumptions, dynamic fee assumptions, maker/taker leakage assumptions, explicit slippage models, and reproducible configuration.

Backtests are approval inputs, not live-trading authorization.

### paper exchange

The paper exchange simulates venue behavior for approved paper orders. It owns simulated order acceptance, rejection, fills, cancellations, fees, funding assumptions, balances, positions, and reconciliation events.

It should be close enough to Binance USDⓈ-M Futures behavior to test workflows while remaining clearly separate from real exchange connectivity.

### audit service

The audit service records commands, validations, vetoes, approvals, state transitions, order lifecycle events, model decisions, configuration changes, operator actions, and system kill-switch activations.

Audit records should be append-oriented and queryable from the frontend.

### notification service

The notification service sends alerts for risk vetoes, stale data, API failures, kill-switch events, order state changes, approval requests, and operational incidents.

Notifications should never contain secrets.

## 7. Data Stores

### Postgres

Postgres is the primary relational store for users, roles, commands, audit records, order intents, order state, approvals, configuration metadata, model decision records, portfolio snapshots, and reconciliation state.

Critical records should use durable identifiers, timestamps, status transitions, and optimistic concurrency or equivalent safeguards where state changes matter.

### TimescaleDB or time-series extension

A time-series extension, such as TimescaleDB, should store market data, candles, mark prices, funding rates, account snapshots, risk metrics, portfolio exposure history, model signal history, and operational metrics that need time-window queries.

The architecture should allow this to start as Postgres tables and evolve into a time-series extension as volume grows.

### Redis

Redis should be used for ephemeral state: event fanout, short-lived caches, rate-limit counters, idempotency keys, command locks, session acceleration, and live dashboard state.

Redis must not be the only durable store for commands, orders, audit records, or model decisions.

### object storage

Object storage should hold large immutable artifacts: downloaded market data snapshots, backtest outputs, training datasets, model artifacts, explainability reports, and exported audit bundles.

Object paths should be content-addressed or versioned and referenced from durable metadata in Postgres.

### model registry

The model registry tracks model versions, artifact locations, feature versions, training windows, validation windows, test windows, metrics, approval status, deployment status, and owners.

Only approved model versions should be eligible for serving, and serving eligibility is separate from permission to place live orders.

## 8. Event Flow

Events provide state propagation, observability, and reconciliation. Commands remain request/response for the critical approval path; events carry resulting facts.

Typical event categories include:

- `command.received`
- `command.validated`
- `command.rejected`
- `risk.vetoed`
- `risk.approved`
- `portfolio.checked`
- `execution.accepted`
- `execution.rejected`
- `order.submitted`
- `order.acknowledged`
- `order.partially_filled`
- `order.filled`
- `order.canceled`
- `order.expired`
- `reconciliation.updated`
- `model.decision_recorded`
- `market_data.stale`
- `kill_switch.activated`

Events should include correlation identifiers so a frontend action can be traced through validation, risk, portfolio, execution, reconciliation, audit, and notification. Fee assumptions, expected-edge calculations, maker/taker outcomes, and no-trade decisions should also be traceable when they affect a decision.

## 9. Command Lifecycle

A command is an operator or system request to do something. An order intent is one possible command type.

```text
Frontend command
  -> authentication
  -> authorization
  -> schema validation
  -> operator-mode, venue, credential, gate, and lane validation
  -> idempotency check
  -> command audit record
  -> domain validation
  -> risk evaluation when applicable
  -> portfolio evaluation when applicable
  -> execution evaluation when applicable
  -> command result
  -> event publication
  -> frontend state update
```

The command lifecycle should reject early when authentication, authorization, schema, mode, or idempotency checks fail. Rejections that matter operationally should be audited.

Manual commands and AI-assisted commands share the same backend lifecycle. The command source changes metadata and approval requirements; it does not change risk authority.

## 10. Order Lifecycle

An order lifecycle begins after a command requests an order intent.

```text
Order intent
  -> intent validation
  -> audit record
  -> risk checks
  -> portfolio checks
  -> execution checks
  -> venue translation
  -> submission to paper exchange or external venue
  -> venue acknowledgement or rejection
  -> fill/cancel/expire tracking
  -> reconciliation
  -> portfolio update
  -> frontend update
```

Each order should have stable internal identifiers and venue identifiers when applicable. Reconciliation must tolerate duplicate events, delayed updates, partial fills, cancellations, rejected orders, and venue API errors.

Order state transitions should be explicit and monotonic where possible. Terminal states should not be overwritten without a corrective reconciliation record.

## 11. Hedge Mode Abstraction

Hedge mode must represent independent `LONG` and `SHORT` books for each symbol. The system must not rely only on net exposure when decisions depend on side-specific position state.

A hedge-mode symbol book should track, at minimum:

- Symbol.
- Venue.
- Margin asset.
- Long quantity, entry price, unrealized PnL, realized PnL, margin, liquidation estimate, and open reduce-only orders.
- Short quantity, entry price, unrealized PnL, realized PnL, margin, liquidation estimate, and open reduce-only orders.
- Side-specific exposure and portfolio contribution.
- Symbol-level gross exposure and net exposure.

Commands must carry an explicit hedge side when the venue requires it. Reduce-only and close-intent behavior must be validated against the intended side-specific book. Binance-specific hedge-mode and `positionSide` constraints are documented in [Binance USDⓈ-M Constraints](../binance/binance_usdm_constraints.md).

## 12. Risk Engine Responsibilities

The risk engine is responsible for independent safety decisions. It should be deterministic, explainable, testable, and isolated from strategy implementation.

Responsibilities include:

- Enforce operator-mode, venue-target, credential-scope, trading-gate, and autonomy-stage restrictions.
- Enforce max daily loss.
- Enforce max symbol exposure.
- Enforce max portfolio exposure.
- Enforce side-specific hedge-mode limits.
- Enforce cross-margin-aware exposure limits where applicable.
- Enforce funding exposure limits where applicable.
- Enforce liquidation buffer requirements.
- Enforce max open orders and order rate limits.
- Enforce stale market data kill switches.
- Enforce stale account or portfolio data kill switches.
- Enforce API error kill switches.
- Enforce manual panic controls.
- Validate risk inputs are fresh and internally consistent.
- Produce human-readable veto reasons.
- Emit auditable approvals and vetoes.

When risk state is unavailable, stale, or contradictory, the risk engine should veto the command.

## 13. Portfolio Engine Responsibilities

The portfolio engine is responsible for current and historical account state across symbols, modes, and venues.

Responsibilities include:

- Maintain balances, margin balances, available margin, and equity snapshots.
- Maintain independent `LONG` and `SHORT` books per symbol in hedge mode.
- Track open orders, reduce-only orders, and pending order effects.
- Calculate gross exposure, net exposure, symbol exposure, and portfolio exposure.
- Calculate hedge ratio, beta exposure, funding exposure, and liquidation buffer where data supports it.
- Track realized PnL, unrealized PnL, fees, and funding assumptions.
- Estimate liquidation distance where venue data supports it.
- Provide pre-trade portfolio checks to risk and execution.
- Reconcile venue or paper-exchange state against internal state.
- Support future multi-symbol portfolio management.

Portfolio calculations should be reproducible and auditable. The portfolio engine should not decide strategy intent.

## 14. Execution Engine Responsibilities

The execution engine is responsible for safe order translation, submission, state tracking, and reconciliation after risk and portfolio approval.

Responsibilities include:

- Validate the approved order intent is still current.
- Confirm the operator-mode, venue-target, credential-scope, trading-gate, and autonomy-stage tuple.
- Translate internal order types into venue-specific requests.
- Preserve hedge side, reduce-only flags, time-in-force, quantity, price, and client order identifiers.
- Reject unsupported order types or unsafe translations.
- Prevent silent conversion into taker orders.
- Enforce maker-first defaults, post-only intent, cancel-if-crossing behavior, and explicit taker gates.
- Include dynamic fees and expected execution costs in order previews and decision records.
- Submit to paper exchange, internal Binance testnet validation lane, or future gated live venue.
- Handle venue acknowledgements, rejections, fills, cancellations, expirations, and API errors.
- Publish execution and reconciliation events.
- Maintain idempotency for retries.

The execution engine must not generate trading strategy decisions.

## 15. Model Decision Record Format

AI-assisted recommendations must produce model decision records before any order intent can proceed.

The target record format should include:

```json
{
  "decision_id": "generated-identifier",
  "timestamp": "iso-8601-timestamp",
  "operator_mode": "paper",
  "venue_target": "internal_paper",
  "credential_scope": "none",
  "trading_gate": "locked",
  "autonomy_stage": "suggest_only",
  "mlops_approval_state": "paper_approved",
  "symbol": "BTCUSDC",
  "model_id": "registered-model-name",
  "model_version": "registered-version",
  "feature_version": "feature-set-version",
  "training_window": {
    "start": "iso-8601-timestamp",
    "end": "iso-8601-timestamp"
  },
  "input_window": {
    "start": "iso-8601-timestamp",
    "end": "iso-8601-timestamp"
  },
  "features_hash": "content-hash",
  "prediction": {
    "direction": "long_short_flat_or_no_action",
    "confidence": 0.0,
    "horizon": "configured-horizon"
  },
  "recommendation": {
    "action": "no_action_or_order_intent",
    "side": "LONG_or_SHORT_when_applicable",
    "order_type": "candidate-order-type",
    "quantity_policy": "sizing-policy-reference"
  },
  "costs": {
    "fee_source": "configured-or-venue-source",
    "maker_fee": "decimal-string",
    "taker_fee": "decimal-string",
    "expected_edge_after_costs": "decimal-string"
  },
  "explanation": {
    "summary": "human-readable rationale",
    "top_features": [],
    "known_limitations": []
  },
  "risk_context": {
    "risk_profile": "configured-risk-profile",
    "risk_status": "not_checked_or_checked",
    "veto_reason": null
  },
  "approval_state": "recorded_pending_rejected_or_approved",
  "correlation_id": "command-correlation-id"
}
```

The record is not an execution approval. It is an auditable explanation of why an AI-assisted recommendation or no-trade decision exists.

## 16. Manual Trading From Frontend

Manual trading begins with an operator action in the frontend. The frontend should expose clear controls for symbol, hedge side, order type, quantity, price, time-in-force, reduce-only or close intent, maker-first policy, primary operator mode, internal lane/gate state, fee assumptions, expected edge after costs, and confirmation.

Manual orders must still pass backend validation, risk checks, portfolio checks, execution checks, audit recording, and reconciliation. A manual action is not privileged over the risk engine.

The frontend should display the approval path, veto reason, order state, reconciliation state, and portfolio impact.

## 17. AI-assisted Trading From Frontend

AI-assisted trading begins with model output displayed in the frontend as a recommendation, not as an automatic venue action.

The frontend should show the model decision record, explanation, confidence, input window, feature version, model version, risk context, fee assumptions, expected edge after costs, no-trade rationale, and proposed order intent. The operator may accept, reject, or adjust a recommendation depending on mode and permissions.

Accepted AI-assisted orders enter the same command and order lifecycle as manual orders. The model service cannot bypass risk, portfolio, execution, audit, or live-trading gates.

## 18. Paper Trading Design

Paper trading should be the first full execution target. It validates the platform control path without venue risk.

The paper exchange should:

- Accept only approved order intents.
- Simulate order acceptance, rejection, fills, partial fills, cancellations, and expirations.
- Apply explicit fee and funding assumptions.
- Apply dynamic fee assumptions and preserve the fee source in audit records.
- Maintain paper balances, positions, open orders, and hedge-mode books.
- Use market data and order book inputs with recorded timestamps.
- Emit reconciliation events like a real venue adapter.
- Support replay tests and deterministic scenarios.

Paper results should be clearly labeled and kept separate from internal testnet validation and live state.

## 19. Testnet Design

The Binance testnet validation lane is the first external venue integration target. Binance USDⓈ-M Futures testnet should be used to validate authenticated backend signing, order translation, API error handling, rate limits, exchange filters, maker-first execution, dynamic fee assumptions, hedge-mode parameters, and reconciliation.

Testnet credentials must be restricted, stored outside source control, and used only by backend services. The browser must never receive them.

Testnet behavior may differ from live behavior, so passing testnet checks is required but not sufficient for live trading approval.

## 20. Live Trading Gates

Live trading is disabled by default.

Before a live-trade workflow can submit an order, all of the following must be true:

- Environment allows live operation.
- Config sets `operator_mode` to `live`.
- Config sets `venue_target` to `binance_live`.
- Config sets `credential_scope` to `trading`.
- Config sets `trading_gate` to an explicitly approved live-trading gate.
- Config explicitly enables live trading.
- Auth service confirms the operator has live-trade permission.
- Human approval requirements are satisfied.
- Exchange credentials are present only in the approved backend secrets backend.
- Credentials are restricted to required trading permissions.
- Withdrawals are disabled.
- IP allowlisting is enabled where possible.
- Risk engine is healthy and approving commands.
- Portfolio engine is healthy and current.
- Execution engine is healthy and configured for the live venue.
- Market data and account data are fresh.
- API error kill switch is not active.
- Manual panic halt is not active.
- Audit service is writable.
- Tests covering live gates are passing.
- Dynamic fee assumptions and expected-edge calculations are recorded.
- Maker/taker policy gates are active.

Failure of any gate must prevent live order submission.

## 21. Security Model

The security model separates browser control from backend authority and exchange signing.

Security requirements include:

- Exchange secrets never reach the frontend.
- Backend services sign exchange requests.
- Secrets are never committed.
- Restricted API keys are required.
- Read-only and trading keys are separate.
- Withdrawals are never enabled.
- IP allowlisting is used where possible.
- Authenticated sessions are required for all operator actions.
- Authorization is role-based and mode-aware.
- Sensitive actions require audit records.
- Live-trade actions require explicit permissions and approvals.
- Logs and notifications must not include secrets.
- Strategies and models must never directly call the exchange connector.

The platform should assume frontend input is untrusted, even when the frontend is private.

## 22. CI/CD Model

CI should enforce repository discipline before changes merge.

Expected checks include:

- Formatting and linting for frontend and backend code when those stacks are introduced.
- Unit tests for risk, portfolio, execution, schemas, and config gates.
- Integration tests for command lifecycle and paper exchange workflows.
- Replay tests for market data and reconciliation.
- Security checks for secret-like values.
- Documentation checks for architecture-changing pull requests.
- Docker or compose validation for local development scaffolding.

Deployment should separate environments by mode. Live-trade deployment should require additional approvals beyond normal CI success.

## 23. MLOps Model

MLOps must make model behavior reproducible, inspectable, and governable.

The MLOps flow should include:

- Versioned raw and processed data windows.
- Versioned feature definitions.
- Training jobs with recorded configuration and code version.
- Backtest jobs with explicit assumptions.
- Microstructure research features for order book imbalance, microprice, spread, depth, trade aggression, fill probability, adverse selection, and latency-adjusted returns.
- Evaluation metrics stored with model artifacts.
- Model registry entries for every candidate.
- Approval states for `research_candidate`, `backtest_approved`, `paper_approved`, `testnet_validated`, `live_readonly_validated`, `live_trade_candidate`, and `live_trade_approved`.
- Model decision records for every served recommendation.
- Explainability output suitable for frontend review.

No model approval state should permit bypassing risk or live-trading gates.

## 24. Observability and Monitoring

The platform should expose operational health, trading workflow health, and risk health.

Monitoring should cover:

- API latency, error rates, and saturation.
- Market data freshness and sequence integrity.
- Order book freshness and spread/liquidity warnings.
- Command rejection and veto rates.
- Risk-engine health and kill-switch state.
- Portfolio reconciliation drift.
- Execution submission latency and venue error rates.
- Maker/taker leakage and post-only rejection rates.
- Dynamic fee source freshness.
- Paper exchange simulation health.
- Model service latency, model version, and decision volume.
- Training and backtest job status.
- Audit write failures.
- Notification delivery failures.

The frontend should surface critical operational state clearly, especially stale data, risk vetoes, panic halts, API error kill switches, and live-trading gate status.

## 25. Failure Modes

The system should fail closed for trading actions.

Important failure modes include:

- Stale market data.
- Stale account or portfolio data.
- Missing order book updates.
- Exchange API errors or rate limits.
- Partial fills with delayed reconciliation.
- Duplicate command submission.
- Network timeouts during submission or cancellation.
- Redis outage.
- Postgres write failure.
- Audit service unavailable.
- Model service unavailable.
- Risk engine unavailable.
- Portfolio engine unavailable.
- Execution engine unavailable.
- Configuration mismatch between frontend display and backend mode.
- Operator panic halt.
- Live credential misconfiguration.
- Expired fee promotion or stale fee assumption.
- Unexpected taker leakage.

For trading commands, unavailable risk, portfolio, execution, or audit dependencies should block the command. Read-only views may degrade with clear stale-state indicators.

## 26. Future Roadmap

The roadmap should move from safe control surfaces to increasingly realistic execution modes:

The detailed phase-gated implementation roadmap lives in [Developer Roadmap](../roadmap/developer_roadmap.md). The summary below is intentionally shorter than that implementation plan.

1. Build the frontend control tower with `PAPER` and `LIVE` primary mode indicators, audit views, lane status, and explicit gate indicators.
2. Define shared schemas for commands, order intents, risk decisions, portfolio snapshots, model decisions, and execution events.
3. Implement command validation, audit records, and risk veto scaffolding.
4. Implement paper exchange workflows and replayable tests.
5. Add portfolio accounting with hedge-mode independent books.
6. Add cross-margin-aware exposure, hedge ratio, beta exposure, funding exposure, and liquidation-buffer calculations.
7. Add model decision records and frontend review for AI-assisted recommendations.
8. Add market microstructure research for order book imbalance, microprice, spread, depth, trade aggression, fill probability, queue approximation, adverse selection, and latency-adjusted returns.
9. Integrate the Binance USDⓈ-M Futures testnet validation lane with backend-only signing.
10. Add dynamic fee policy, maker-first execution, taker leakage monitoring, reconciliation, kill switches, and operational monitoring.
11. Add MLOps registry, training jobs, backtest jobs, and approval workflows.
12. Add `LIVE` read-only capability with restricted read-only credentials and `trading_gate=locked`.
13. Consider live-trade capability only after explicit human approval, tested gates, operational runbooks, and independent risk controls are mature.

The platform should remain buildable in small increments. Each step should preserve the core principle: frontend controls everything, backend validates everything, risk can veto everything, and secrets never touch the frontend.
