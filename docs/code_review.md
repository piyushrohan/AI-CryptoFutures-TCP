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
- Can this change silently create market orders, taker behavior, or unsafe defaults?
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
- Any withdrawal-related capability.
- Any default that enables live trading.
- Any risk-engine bypass for trading commands.

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
- Portfolio exposure or margin logic that does not support future multi-symbol management.
- Model decision output that is not explainable or auditable.

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

### Operating Modes and Live Gates

Confirm `observe`, `paper`, `testnet`, `live-readonly`, and `live-trade` behavior remains explicit. Live trading must be disabled by default and unavailable unless every required gate is deliberately enabled.

Changes that affect mode handling need tests for safe defaults and rejection paths.

### Risk Independence

Risk logic must stay independent from strategy and model logic. A strategy or model can propose an action, but it cannot approve its own risk or call execution directly.

Manual orders from the frontend must still pass risk checks.

### Portfolio and Hedge Mode

Review hedge-mode behavior as independent `LONG` and `SHORT` books. Do not accept changes that collapse side-specific state into net exposure when liquidation, margin, reduce-only behavior, PnL, or execution semantics depend on side.

Portfolio changes should support future multi-symbol exposure and margin checks.

### Execution Behavior

Execution code should translate approved intent into venue-specific payloads without changing the meaning of the order. It must preserve hedge side, reduce-only flags, time-in-force, quantity, price, and client order identifiers.

Any market/taker behavior must be explicit, reviewed, documented, tested, and gated where appropriate.

### Model Decisions

Model service changes should produce decision records, not direct orders. Decision records must be explainable and auditable, including model version, feature version, input window, confidence, recommendation, and rationale.

AI-assisted orders must enter the same validation, risk, portfolio, execution, audit, and reconciliation lifecycle as manual orders.

### Tests and Coverage

Risk, execution, hedge-mode, live-gate, and config-default changes require deterministic tests. The repository target is over 98% test coverage for implemented code, with stronger expectations for safety-critical modules.

Avoid tests that require live Binance connectivity. Unit tests must not call Binance.

### Documentation

Architecture changes should update the relevant docs under `docs/`. Command changes should update `README.md`. Safety-sensitive assumptions should be stated plainly.

Docs should remain practical and buildable, with clear boundaries between frontend control, backend validation, risk veto authority, portfolio checks, execution translation, model decision records, and exchange connectivity.
