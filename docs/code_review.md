# Code Review Guide

This guide defines how to review changes to AI-CryptoFutures-TCP. It applies to AI coding agents and human contributors.

The review posture is conservative because this repository is for a trading control platform. The platform must protect secrets, prevent accidental live trading, keep risk checks independent, and preserve clear operator control.

## Review Priorities

Reviewers should look first for safety, security, and trading-control failures. Style and refactoring concerns are secondary to secret handling, live-trading gates, risk enforcement, execution behavior, hedge-mode correctness, and auditability.

Every review should ask:

- Can this change expose, commit, log, print, or transmit secrets?
- Can this change place or prepare live orders without explicit gates?
- Can this change bypass risk, portfolio, execution, or audit checks?
- Can frontend code sign exchange requests or call authenticated exchange endpoints directly?
- Can a strategy or model call the exchange connector directly?
- Can model governance mark a recommendation executable without a complete `ModelDecisionRecord`?
- Can this change silently create market orders, taker behavior, or unsafe defaults?
- Can this change hard-code fees, assume permanent zero maker fees, or skip expected-edge-after-costs calculations?
- Can this change leak maker-first intent into taker fills without explicit gates and audit records?
- Can this change weaken microstructure execution checks such as post-only intent, cancel-if-crossing, queue approximation, fill probability, or adverse-selection handling?
- Can this change make `ETHBTC` or `SYN_ETHBTC` executable without an explicit symbol-universe policy change?
- Does hedge-mode behavior preserve independent `LONG` and `SHORT` books?
- Are risk, execution, config default, and live-gate tests present where needed?
- Are architecture or operator-facing behavior changes documented?

## Severity Definitions

### P0: Must Fix Before Merge

P0 issues are release-blocking safety or security failures.

Flag as P0:

- Any secret-handling weakness.
- Any committed, printed, logged, or frontend-exposed secret.
- Any live-trading bypass.
- Any frontend exchange-signing path.
- Any endpoint or worker that can place live orders without explicit live-trading gates.
- Any path that allows a strategy or model to directly call an exchange connector.
- Any model or strategy recommendation converted to an order intent without a complete decision record and normal downstream checks.
- Any withdrawal-related capability.
- Any default that enables live trading.
- Any risk-engine bypass for trading commands.
- Any strategy or model path that directly calls the exchange connector.

### P1: Must Fix Before Merge Unless Explicitly Deferred

P1 issues are high-risk correctness, test, or design gaps.

Flag as P1:

- Missing risk tests for changed risk behavior.
- Missing execution translation tests for changed execution behavior.
- Missing hedge-mode tests when side-specific position behavior changes.
- Missing live-trading gate tests when modes, config, or execution paths change.
- Missing config default tests for safety-sensitive settings.
- Unclear trading behavior.
- Undocumented architecture changes.
- Silent introduction of market orders, taker behavior, or order aggressiveness changes.
- Static or undocumented fee assumptions in trading, backtest, paper, model, or execution decisions.
- Treating direct `ETHBTC` as executable or full-depth required before the BTCUSDC/ETHUSDC synthetic path is approved.
- Treating `SYN_ETHBTC` as a venue symbol rather than a derived non-executable series.
- Missing expected-edge-after-costs calculation where a decision depends on edge.
- Missing maker/taker leakage tests for changed execution behavior.
- Unclear post-only, cancel-if-crossing, fill-probability, queue, adverse-selection, or latency behavior.
- Portfolio exposure or margin logic that does not support future multi-symbol management.
- Model decision output that is not explainable or auditable.
- Binance testnet validation code that performs network calls or request signing in unit tests.
- `LIVE` read-only code that can submit, cancel, or replace orders.

### P2: Should Fix Soon

P2 issues are maintainability or operational concerns that do not create immediate trading or secret-handling risk.

Examples include unclear naming, duplicated validation, weak error messages, incomplete observability, missing non-critical docs, or insufficient type precision outside safety-critical paths.

### P3: Nice To Have

P3 issues are polish suggestions. They should not distract from P0/P1 review.

Examples include minor wording, formatting, comments, naming preferences, or optional refactors.

## Required Review Areas

### Secrets and Security

Confirm secrets are not committed, printed, logged, sent to the frontend, embedded in tests, or represented by realistic placeholder values. Exchange signing must remain backend-only.

Restricted API keys, IP allowlisting, separate read-only and trading keys, and disabled withdrawals should remain core assumptions for future exchange access.

### Operator Modes, Internal Lanes, and Live Gates

Confirm the frontend exposes only `PAPER` and `LIVE` as primary operator modes. `observe_only` is an autonomy stage or session state, Binance testnet is an internal validation lane, `LIVE` read-only is `operator_mode=live` with `credential_scope=read_only` and `trading_gate=locked`, and live-trade capability is `operator_mode=live` with trading credentials and explicit live gates.

The two-mode UI must not hide or bypass live gates, MLOps approval state, risk checks, portfolio checks, execution checks, audit, or reconciliation. Live trading must be disabled by default and unavailable unless every required gate is deliberately enabled.

MLOps approval state must never be treated as execution authorization. Reviewers should reject any path where model or strategy readiness bypasses risk gates, live gates, portfolio checks, execution checks, audit, or reconciliation.

Changes that affect `operator_mode`, `venue_target`, `credential_scope`, `trading_gate`, `autonomy_stage`, or `mlops_approval_state` need tests for safe defaults and rejection paths.

### Risk Independence

Risk logic must stay independent from strategy and model logic. A strategy or model can propose an action, but it cannot approve its own risk or call execution directly.

Manual orders from the frontend must still pass risk checks.

### Portfolio and Hedge Mode

Review hedge-mode behavior as independent `LONG` and `SHORT` books. Do not accept changes that collapse side-specific state into net exposure when liquidation, margin, reduce-only behavior, PnL, or execution semantics depend on side.

Portfolio changes should support future multi-symbol exposure and margin checks.

### Execution Behavior

Execution code should translate approved intent into venue-specific payloads without changing the meaning of the order. It must preserve hedge side, reduce-only flags, time-in-force, quantity, price, and client order identifiers.

Any market/taker behavior must be explicit, reviewed, documented, tested, and gated where appropriate.

Maker-first behavior should be the default. Reviewers should check post-only intent, cancel-if-crossing policy, max taker leakage, queue position approximation, fill probability, adverse-selection assumptions, latency handling, spread capture measurement, and cancel/replace discipline.

Fee assumptions must be dynamic, configurable, audited, and included in expected-edge calculations. Reviewers should reject permanent hard-coded zero maker fees and any change that treats a fee promotion as permanent.

For the initial BTC/ETH focus, reviewers should confirm that `BTCUSDC` and `ETHUSDC` are the only executable instruments, `SYN_ETHBTC` remains derived and non-executable, and direct `ETHBTC` remains disabled reference-only data unless a reviewed policy change says otherwise.

### Model Decisions

Model service changes should produce decision records, not direct orders. Decision records must be explainable and auditable, including model version, feature version, input window, confidence, recommendation, and rationale.

AI-assisted orders must enter the same validation, risk, portfolio, execution, audit, and reconciliation lifecycle as manual orders.

Microstructure models should include no-trade decisions and should report expected edge after fees, spread, slippage, adverse selection, funding, and latency costs when those features affect the recommendation.

### Tests and Coverage

Risk, execution, hedge-mode, live-gate, and config-default changes require deterministic tests. The repository target is over 98% test coverage for implemented code, with stronger expectations for safety-critical modules.

Avoid tests that require live Binance connectivity. Unit tests must not call Binance.

Execution tests should cover maker-first defaults, post-only translation, cancel-if-crossing behavior, taker leakage gates, dynamic fee assumptions, and expected-edge-after-costs calculations.

### Documentation

Architecture changes should update the relevant docs under `docs/`. Command changes should update `README.md`. Safety-sensitive assumptions should be stated plainly.

Docs should remain practical and buildable, with clear boundaries between frontend control, backend validation, risk veto authority, portfolio checks, execution translation, model decision records, and exchange connectivity.

Binance-specific implementation should be checked against `docs/binance/binance_usdm_constraints.md` and `docs/binance/fee_and_symbol_policy.md`. Maker-first execution should be checked against `docs/execution/maker_microstructure_execution.md`.
