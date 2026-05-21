# Contributor Instructions

These instructions apply to all AI coding agents and human contributors working in this repository. Treat this file as a safety contract for changes to AI-CryptoFutures-TCP.

For code review severity guidance, see [docs/code_review.md](docs/code_review.md).

## 1. Project Identity

- Project: AI-CryptoFutures-TCP.
- TCP: Trading Control Platform.
- Product direction: frontend-first AI crypto futures trading control platform.

This is not a simple trading bot. The frontend is the operator control tower, the backend is the enforcement boundary, and every future trading action must remain auditable, risk-checked, and mode-gated.

## 2. Non-negotiable Safety Rules

- Never commit secrets.
- Never print secrets.
- Never store Binance secrets in frontend code.
- Never let browser code sign exchange requests.
- Never bypass risk checks.
- Never enable live trading by default.
- Never add market/taker order behavior silently.
- Never assume hedge mode is per-symbol only; represent hedge-mode state with explicit independent `LONG` and `SHORT` books where position behavior depends on side.
- Never create endpoints that place live orders without explicit live-trading gates.
- Never allow a strategy or model to directly call the exchange connector.
- Never make withdrawals available.
- Never commit generated market data, model artifacts, checkpoints, local databases, logs, or cache output.
- Never add realistic placeholder credentials, tokens, passwords, API keys, signing keys, or JWT secrets.

When in doubt, fail closed and keep the behavior read-only or simulated.

## 3. Architecture Rules

- Frontend sends intent.
- API validates commands.
- Risk engine approves or rejects.
- Portfolio engine checks exposure and margin.
- Execution engine translates approved intent into exchange-specific order payloads.
- Audit service records every command and decision.
- Model service produces decision records, not direct orders.

All order intents must move through command validation, audit recording, risk checks, portfolio checks, execution checks, execution translation, submission to an approved venue or simulator, reconciliation, and frontend update.

Strategies and models may propose actions, but their output is untrusted until backend validation, independent risk approval, portfolio approval, and execution approval have completed.

## 4. Testing Rules

- Add tests for risk logic.
- Add tests for execution translation.
- Add tests for hedge-mode behavior.
- Add tests for live-trading gates.
- Add tests for config defaults.
- Prefer deterministic tests.
- Make sure to get over 98% test coverage for implemented code.
- Do not connect to Binance in unit tests.
- Add regression tests for rejected commands, vetoes, stale data handling, panic controls, and unsafe mode transitions.

Tests should prove dangerous behavior is disabled by default. Missing tests around risk, execution, hedge mode, and live gates should block changes that touch those areas.

## 5. Documentation Rules

- Update docs when architecture changes.
- Update README when commands change.
- Explain assumptions.
- Keep decision records understandable.
- Update risk, execution, security, MLOps, or Binance docs when changing those boundaries.
- Document new operating modes, live-trading gates, secret-handling expectations, and order lifecycle changes before relying on them.

Documentation should describe buildable behavior, not vague intent. If a decision affects operator safety, exchange access, live-trading gates, or model governance, make it explicit.

## 6. Code Review Guidelines

- Flag any secret-handling weakness as P0.
- Flag any live-trading bypass as P0.
- Flag any frontend exchange-signing path as P0.
- Flag missing risk tests as P1.
- Flag unclear trading behavior as P1.
- Flag undocumented architecture changes as P1.

Use [docs/code_review.md](docs/code_review.md) for the full review checklist and severity definitions.

## 7. Implementation Style

- Small, reviewable changes.
- Strong typing.
- Clear boundaries.
- No hidden side effects.
- No silent defaults for dangerous behavior.
- Prefer explicit config over magic behavior.
- Prefer mode-gated, auditable workflows over implicit execution paths.
- Keep trading strategy logic separate from risk, portfolio, and execution enforcement.
- Keep commits focused and explain why safety-relevant behavior changed.
- Add TODO markers only when they are specific, actionable, and tied to a clear owner or follow-up.

Implementation should make unsafe behavior hard to express. If a change touches trading intent, secrets, risk, execution, portfolio accounting, or model-driven decisions, design the interfaces so validation and review are unavoidable.
