# Developer Roadmap

This roadmap defines the intended build order for AI-CryptoFutures-TCP. It is phase-gated, not calendar-based.

The roadmap is intentionally frontend-first and safety-first. The platform should become an operator control tower with only two primary user-facing modes, `PAPER` and `LIVE`, while internal lanes and gates handle observation, Binance testnet validation, live read-only visibility, live-trade approval, training, evaluation, backtesting, strategy sessions, model deployment, panic controls, and audit inspection. It must not become an opaque trading bot.

This document is documentation only. It does not implement application code, Binance connector code, strategy logic, live trading, or secrets.

Implementation status for the deterministic local MVP of phases 3 through 6 is
tracked in [Phase 3-6 Implementation Status](phase_3_6_implementation_status.md).

## Roadmap Principles

- Frontend controls everything.
- Backend validates everything.
- Risk engine can veto everything.
- Secrets never touch the frontend.
- Live trading is disabled by default.
- The browser never receives exchange secrets and never signs exchange requests.
- Strategies and models never directly call the exchange connector.
- `PAPER` is the first full user-facing mode.
- `LIVE` is introduced later, initially as read-only.
- Binance USDⓈ-M Futures testnet is an internal validation lane, not a top-level operator mode.
- The preferred initial strategy universe is USDC-quoted Binance USDⓈ-M Futures perpetual pairs, such as `BTCUSDC` and `ETHUSDC`, subject to current dynamic fee, liquidity, funding, and risk policy. The first BTC/ETH focus treats `SYN_ETHBTC` as a derived non-executable series and direct `ETHBTC` as disabled reference-only data.
- Portfolio Margin is later research after cross-margin-aware accounting matures.

## Mode State Model

The frontend primary mode switch should show only:

- `PAPER`
- `LIVE`

Internal state must still preserve:

- `operator_mode`: `paper`, `live`
- `venue_target`: `internal_paper`, `binance_testnet`, `binance_live`
- `credential_scope`: `none`, `read_only`, `trading`
- `trading_gate`: `locked`, `approval_required`, `tiny_live`, `armed`, `halted`
- `autonomy_stage`: `observe_only`, `suggest_only`, `human_approval`, `paper_auto`, `testnet_auto`, `tiny_live_auto`, `scaled_live_auto`
- `mlops_approval_state`: `research_candidate`, `backtest_approved`, `paper_approved`, `testnet_validated`, `live_readonly_validated`, `live_trade_candidate`, `live_trade_approved`

Observe is an autonomy stage or session state, not a top-level operator mode. `LIVE` read-only is `operator_mode=live`, `credential_scope=read_only`, and `trading_gate=locked`. Live-trade capability is `operator_mode=live`, `credential_scope=trading`, and explicit live trading gates.

## Recurring Gates

These gates apply to every phase once the related capability exists.

- No strategy session may run unless the fee model is available, current, configurable, auditable, and included in `expected_edge_after_costs`.
- Every strategy decision must calculate `expected_edge_after_costs` using current maker fee, taker fee, expected slippage, funding, and adverse-selection estimates.
- Fee and symbol policy must be dynamic, configurable, and auditable.
- The system must not assume that any Binance maker-fee promotion is permanent.
- Maker-first execution is the default.
- Taker behavior must be explicit, gated, tested, and audited.
- Hedge mode is not free alpha. It is allowed only to express separable intents with independent `LONG` and `SHORT` books.
- Risk gates, audit records, and safe config defaults must be present before execution behavior expands.
- MLOps approval states may indicate model or strategy readiness, but they must never bypass risk gates, live gates, portfolio checks, execution checks, audit, or reconciliation.

## Phase 0: Product Contract and Frontend Control Map

### Purpose

Establish the product contract before implementation. Define the platform as a frontend-first Trading Control Platform, not an AI agent that directly trades.

### Frontend Screens and Actions Unlocked

- Product shell and navigation plan.
- Frontend control-surface map.
- Operator action catalog for `PAPER`, `LIVE`, observe-only session state, paper trading, internal testnet validation, training, evaluation, backtesting, strategy session start/stop, model deployment request, manual order intent, approval/rejection, panic cancel, panic flatten, and audit inspection.
- Two-mode frontend map showing how each visible action maps to backend `operator_mode`, `venue_target`, `credential_scope`, `trading_gate`, `autonomy_stage`, and `mlops_approval_state`.

### Backend Capabilities Required

- Command catalog draft.
- Command ownership boundaries.
- Initial service boundary map.
- Documentation links from contributor guidance to architecture, risk, execution, Binance, and roadmap docs.
- Preferred initial USDC-quoted universe documented as `BTCUSDC` and `ETHUSDC`, subject to current dynamic fee and liquidity policy.

### Risk and Safety Gates

- Every operator action maps to a backend command.
- No frontend page may be designed as a direct exchange-control path.
- No strategy, model, or frontend action may bypass backend validation.
- Live trading remains out of scope.

### Testing and Acceptance Gates

- Roadmap, system design, frontend control surface, Binance constraints, fee policy, and contributor docs are internally consistent.
- Review checklist flags missing command mapping as a design issue.
- Documentation states that no browser code signs exchange requests.

### Not Allowed Yet

- Application feature code.
- Binance connector code.
- Strategy implementation.
- Live trading implementation.
- Secrets or placeholder secrets that look real.

## Phase 1: Safety Spine and CI Baseline

### Purpose

Build the first implementation spine around safe defaults, command validation direction, auditability, and engineering discipline. This phase prepares `PAPER` as the first full user-facing mode with observe-only session state available inside it.

### Frontend Screens and Actions Unlocked

- Local landing/control shell.
- `PAPER` dashboard placeholder.
- Mode and gate status display.
- Risk status placeholder.
- Audit viewer placeholder.
- Panic controls shown as unavailable until backend support exists.

### Backend Capabilities Required

- Safe config defaults: `operator_mode=paper`, `venue_target=internal_paper`, `credential_scope=none`, `trading_gate=locked`, `autonomy_stage=observe_only`, and `live_trading_enabled=false`.
- Initial API command validation direction.
- Audit scaffolding.
- Risk-gate scaffolding.
- Panic command definitions.
- Local bootstrap direction around `make up`.

### Risk and Safety Gates

- Live trading is disabled by default in config and tests.
- Unsafe lanes and gates fail closed.
- Commands that would place orders are rejected when `autonomy_stage=observe_only`.
- Secrets are not printed, logged, committed, or sent to the frontend.

### Testing and Acceptance Gates

- CI baseline.
- Linting.
- Unit test runner.
- Secret scanning.
- Dependency checks.
- Documentation checks.
- Safe config default tests.
- Tests proving `autonomy_stage=observe_only` cannot submit orders.
- `make up` acceptance target defined: frontend, API, database, Redis, and monitoring placeholders start; `operator_mode=paper`, `venue_target=internal_paper`, `credential_scope=none`, `trading_gate=locked`, and `autonomy_stage=observe_only` are active; live trading is disabled; no Binance credentials are required.

### Not Allowed Yet

- Paper fills.
- Testnet connectivity.
- `LIVE` read-only connectivity.
- Strategy sessions.
- Model recommendations.

## Phase 2: Deterministic Exchange and Account State

### Purpose

Define the exchange and account truth model before trading workflows depend on it.

### Frontend Screens and Actions Unlocked

- Account-state inspector using local or mocked data.
- Symbol metadata inspector.
- Fee and symbol policy inspector.
- Data freshness indicators.

### Backend Capabilities Required

- `AccountState` schema covering margin mode, position mode, collateral assets, maintenance margin, liquidation distance, unrealized PnL, funding exposure, open orders, symbol filters, tick size, lot size, min notional, and fee policy references.
- Dynamic symbol metadata model.
- Dynamic fee and symbol policy model.
- Preferred USDC-quoted Binance USDⓈ-M Futures universe metadata for pairs such as `BTCUSDC` and `ETHUSDC`, gated by current dynamic fee and liquidity policy.
- Three-asset symbol-universe policy: `BTCUSDC` and `ETHUSDC` executable, `SYN_ETHBTC` derived and non-executable, `ETHBTC` reference-only and disabled by default.
- Exchange-state snapshot storage.
- Staleness and source timestamps.
- Read-only local/mock API inspectors for exchange state, account state, symbol metadata, and fee policy. These inspectors must not connect to Binance or enable execution.

### Risk and Safety Gates

- Account and symbol state must be timestamped and source-labeled.
- Fee assumptions must be current before strategy or order-preview workflows use them.
- Portfolio Margin remains research-only and must not be treated as implemented.
- Hedge mode must be represented as independent `LONG` and `SHORT` books when position behavior depends on side.

### Testing and Acceptance Gates

- Schema tests for account state, symbol filters, fees, and position mode.
- Config tests for safe defaults.
- Tests for stale fee and stale symbol metadata rejection.
- Tests proving fee promotions are time-bounded or explicitly reviewed.

### Not Allowed Yet

- Real Binance account connectivity.
- Order submission.
- Strategy sessions.
- Portfolio Margin implementation.

## Phase 3: Paper Trading Control Loop

### Purpose

Deliver the first `PAPER` MVP. Paper trading proves the frontend command path, risk checks, portfolio updates, execution translation, audit records, and reconciliation without external venue side effects.

### Frontend Screens and Actions Unlocked

- Paper trading dashboard.
- Manual paper order intent form.
- Order preview with fee assumptions and `expected_edge_after_costs`.
- Paper positions and independent hedge books.
- Paper order lifecycle view.
- Paper audit timeline.

### Backend Capabilities Required

- Paper exchange.
- Order lifecycle.
- Maker-first execution policy.
- Dynamic fee model.
- Slippage model.
- Liquidation model.
- Portfolio book updates.
- Reconciliation events.

### Risk and Safety Gates

- Manual paper orders still pass validation, risk checks, portfolio checks, execution checks, audit, and reconciliation.
- No paper strategy session may run unless the fee model is available, current, configurable, auditable, and included in `expected_edge_after_costs`.
- Maker-first is default.
- Taker behavior requires explicit paper-mode gate and test coverage.

### Testing and Acceptance Gates

- Deterministic paper order lifecycle tests.
- Risk veto tests.
- Portfolio update tests for independent `LONG` and `SHORT` books.
- Dynamic fee and expected-edge tests.
- Maker-first and taker leakage tests.
- Replay-ready audit records.

### Not Allowed Yet

- Binance testnet validation lane.
- `LIVE` read-only account access.
- Live trading.
- Autonomous strategies.

## Phase 4: Portfolio and Risk Foundation

### Purpose

Make risk and portfolio controls strong enough to support later strategy sessions. Risk comes before strategy.

### Frontend Screens and Actions Unlocked

- Risk dashboard.
- Portfolio exposure dashboard.
- Hedge-book drill-down.
- Kill-switch status view.
- Funding and liquidation-buffer visibility.

### Backend Capabilities Required

- Max account leverage checks.
- Max symbol exposure checks.
- Max sector exposure checks.
- Max correlated exposure checks.
- Max daily loss and drawdown checks.
- Liquidation-buffer checks.
- Stale data kill.
- API error kill.
- Abnormal spread kill.
- Funding spike kill.
- Volatility halt.
- Order spam protection.

### Risk and Safety Gates

- For cross or portfolio-like modes, risk must be portfolio-level, not symbol-only.
- Risk checks must be independent from strategy logic.
- Missing, stale, or contradictory risk inputs veto trading actions.
- Panic cancel and panic flatten commands must be auditable and permissioned.

### Testing and Acceptance Gates

- Unit tests for each risk rule.
- Integration tests for manual order vetoes.
- Replay tests for stale data, abnormal spread, volatility halt, and funding spike scenarios.
- Tests for portfolio-level exposure and correlated exposure.

### Not Allowed Yet

- Internal testnet validation without passing paper and risk gates.
- Model-driven order intents.
- Portfolio Margin trading assumptions.

## Phase 5: Microstructure Research and Backtesting

### Purpose

Build deterministic research infrastructure before AI models. This phase supports maker-first market microstructure research and backtesting.

### Frontend Screens and Actions Unlocked

- Market data recording status.
- Backtest launcher.
- Backtest report viewer.
- Replay day selector.
- Research feature explorer.

### Backend Capabilities Required

- Order book recorder.
- Trade stream recorder.
- Funding/rate recorder.
- Replay engine.
- Backtest engine.
- Fee model and slippage model integration.
- Feature generation for imbalance, microprice, spread, depth slope, queue imbalance, trade sign imbalance, short-term realized volatility, funding rate, open interest, liquidation prints, BTC dominance proxy, cross-coin correlation, and latency-adjusted mid-price returns.
- Synthetic ETH/BTC feature generation from time-aligned `ETHUSDC` and `BTCUSDC` books, including leg timestamp skew and synthetic spread cost.

### Risk and Safety Gates

- Backtests must include dynamic fees and cost assumptions.
- Results must report maker/taker ratio, fill ratio, fees, adverse selection, missed fills, and latency.
- Backtest approval is not live-trading approval.

### Testing and Acceptance Gates

- Replay tests on historical order book days.
- Deterministic backtest tests.
- Feature correctness tests.
- Cost accounting tests for fees, slippage, funding, adverse selection, and latency.

### Not Allowed Yet

- Real exchange order submission.
- Model deployment to trading workflows.
- Reinforcement learning, online learning, LSTM, or Transformer models.

## Phase 6: Strategy Sessions in Paper Mode

### Purpose

Introduce strategy sessions only after deterministic infrastructure, paper trading, portfolio accounting, and risk gates exist. The first strategy family is maker-first microstructure.

### Frontend Screens and Actions Unlocked

- Strategy session dashboard.
- Start/stop/pause paper strategy session.
- Strategy recommendation viewer.
- Maker/taker leakage monitor.
- Session-level risk limits and panic controls.

### Backend Capabilities Required

- Strategy session manager.
- Maker-first market making/rebate capture policy.
- Microstructure scalp policy.
- Session-level audit records.
- Inventory-aware paper portfolio updates.
- Session-level metrics.

### Risk and Safety Gates

- Hedge mode is used only for separable intents: strategic inventory, tactical microstructure book, risk overlays, funding/basis leg, volatility hedge, or pair/sector hedge.
- Bad hedge mode is rejected when both sides come from the same signal, expected costs exceed edge, or liquidation modeling is incomplete.
- Strategy output is an untrusted recommendation until validated by command, risk, portfolio, execution, and audit workflows.
- No strategy session may run unless the fee model is current and included in `expected_edge_after_costs`.

### Testing and Acceptance Gates

- Simulation tests on every strategy change.
- Strategy session start/stop tests.
- Maker-only discipline tests.
- Toxic flow and adverse-selection scenario tests.
- Hedge-book lifecycle tests proving scalp shorts cannot accidentally close strategic longs.

### Not Allowed Yet

- Testnet auto-trade.
- `LIVE` read-only or live-trade execution.
- AI-driven autonomous execution.
- Direct strategy access to exchange connectors.

## Phase 7: Model Layer and Decision Records

### Purpose

Add transparent AI/ML after deterministic infrastructure and strategy sessions exist. Start simple and keep model output explainable.

### Frontend Screens and Actions Unlocked

- Model registry.
- Experiment tracker.
- Evaluation report viewer.
- Model decision inspector.
- Model deployment request workflow.

### Backend Capabilities Required

- Feature store.
- Experiment tracking.
- Model registry.
- Evaluation jobs.
- Simple models first: logistic regression or LightGBM for short-horizon direction, regression for expected return after fees, toxic-flow classifier, volatility model, and regime classifier.
- `ModelDecisionRecord` schema and storage.

### Risk and Safety Gates

- Every model recommendation must produce a `ModelDecisionRecord` before it can become an order intent.
- The frontend must inspect model version, feature version, input window, prediction, confidence, expected edge after costs, top features, risk context, rejected alternatives, and final explanation.
- Model output is not execution approval.
- Reinforcement learning, LSTM, Transformer, and online learning are later research only.

### Testing and Acceptance Gates

- Model decision record tests.
- Feature versioning tests.
- Evaluation reproducibility tests.
- No-trade decision tests.
- Tests proving models cannot directly call exchange connectors.

### Not Allowed Yet

- Live model trading.
- Internal testnet auto-validation without Phase 8 gates.
- Opaque model decisions.

## Phase 8: Binance Testnet

### Purpose

Integrate the Binance USDⓈ-M Futures testnet validation lane only after `PAPER` workflows are stable.

### Frontend Screens and Actions Unlocked

- Internal testnet validation dashboard.
- Testnet account-state view.
- Testnet order lifecycle view.
- User data stream reconciliation status.
- Testnet venue health and rate-limit display.

### Backend Capabilities Required

- Backend-only Binance testnet signing.
- Dynamic exchange info ingestion.
- Symbol filter validation.
- `positionSide` translation.
- Hedge and one-way mode handling.
- Post-only behavior validation.
- Rate-limit handling.
- User data stream reconciliation.
- Close-intent translation.
- Dynamic fee handling.

### Risk and Safety Gates

- Testnet credentials are separate from live credentials.
- Browser never receives credentials or signs exchange requests.
- Testnet order intents pass the same validation, risk, portfolio, execution, audit, and reconciliation flow as paper orders.
- Testnet remains an internal validation lane, not a top-level operator mode.
- Live trading remains disabled.

### Testing and Acceptance Gates

- Integration tests against testnet-safe boundaries.
- Connector contract tests with mocked responses.
- Position mode tests.
- Symbol filter tests.
- User data stream reconciliation tests.
- Close-long, close-short, reduce-long, and reduce-short tests.

### Not Allowed Yet

- `LIVE` read-only account access.
- Live-trade order submission.
- Portfolio Margin trading.
- Scaled autonomy.

## Phase 9: LIVE Read-only Account Visibility

### Purpose

Add `LIVE` read-only account visibility without any live order submission.

### Frontend Screens and Actions Unlocked

- `LIVE` read-only dashboard.
- Live balance view.
- Live position view.
- Live open-order view.
- Live reconciliation comparison.
- Audit-only live account inspection.

### Backend Capabilities Required

- Restricted read-only credential support.
- Backend-only secret access.
- Live account snapshot ingestion.
- Reconciliation comparison against internal state.
- `LIVE` read-only audit records.

### Risk and Safety Gates

- No order submission when `operator_mode=live`, `credential_scope=read_only`, and `trading_gate=locked`.
- Read-only and trading credentials are separate.
- Withdrawals are never enabled.
- Secrets never reach the browser.
- `LIVE` read-only cannot silently upgrade to live-trade.

### Testing and Acceptance Gates

- Tests proving `LIVE` read-only rejects order submission.
- Secret isolation tests.
- Permission tests.
- Reconciliation comparison tests.
- Audit-only behavior tests.

### Not Allowed Yet

- Live-trade endpoints.
- Tiny live order submission.
- Autonomous live trading.

## Phase 10: Gated Live-trade Research Path

### Purpose

Document and eventually test a tiny live-trade research path. This phase is fundamentally different from `LIVE` read-only and must remain gated.

### Frontend Screens and Actions Unlocked

- Live-trade gate dashboard.
- Human approval workflow.
- Tiny live session request.
- Live-trade runbook viewer.
- Rollback and panic procedure controls.

### Backend Capabilities Required

- Explicit live-trading config gate.
- Restricted trading credential support.
- Human approval records.
- Tiny size limits.
- Strict daily loss cap.
- Maker-only default.
- Rollback procedures.
- Panic cancel and panic flatten procedures.
- Incident and runbook audit records.

### Risk and Safety Gates

- Human approval required.
- Tiny size only.
- Maker-only by default.
- Taker behavior explicitly gated.
- Strict daily loss cap.
- Live-trading config gate explicitly enabled with `operator_mode=live`, `venue_target=binance_live`, `credential_scope=trading`, an approved `trading_gate`, a live-trading `autonomy_stage`, and `mlops_approval_state=live_trade_approved`.
- Risk, portfolio, execution, audit, and notification services healthy.
- Automatic halt on stale data, API errors, abnormal spread, funding spike, volatility halt, reconciliation drift, or taker leakage breach.

### Testing and Acceptance Gates

- Live-trading gate tests.
- Tiny size limit tests.
- Daily loss cap tests.
- Panic cancel and panic flatten tests.
- Rollback drill tests.
- Canary deployment and automatic rollback checks.
- Paper-trading and testnet approval history reviewed before any live consideration.

### Not Allowed Yet

- Scaled live autonomous trading.
- Portfolio Margin live trading.
- Ungated taker behavior.
- Any strategy or model direct exchange access.

## Institutional Engineering Gates

Every phase should maintain or improve:

- Unit tests on every pull request.
- Simulation tests on every strategy change.
- Replay tests on historical order book days.
- Paper-trading approval gates.
- Config versioning.
- Model registry.
- Feature store.
- Experiment tracking.
- Canary deployment planning.
- Automatic rollback planning.
- Documentation updates for architecture changes.

Monitoring should eventually cover PnL, realized and unrealized PnL, fees, maker/taker ratio, fill ratio, adverse selection, latency, missed fills, liquidation distance, position drift, and model confidence drift.

## Roadmap Acceptance Criteria

The roadmap is satisfied when:

- This file is linked from `README.md`, `AGENTS.md`, and `docs/architecture/system_design.md`.
- Phases 0 through 10 are present.
- `LIVE` read-only is separate from live-trade research.
- Frontend control-surface mapping comes before implementation.
- Safety Spine is first.
- `PAPER` is the first full user-facing mode.
- Binance testnet is an internal validation lane after paper.
- Portfolio Margin is later research.
- Live trading is disabled by default.
- Browser secrets and browser signing are forbidden.
- Strategy and model direct exchange access is forbidden.
- No strategy session can run without current fee policy and `expected_edge_after_costs`.
