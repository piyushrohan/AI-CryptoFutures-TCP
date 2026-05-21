# AI Agent Instructions

This repository is for AI-CryptoFutures-TCP, a Trading Control Platform for crypto futures workflows. Future coding agents must preserve the safety boundaries in this file.

## Non-Negotiable Rules

- Never add real secrets, credentials, API keys, tokens, passwords, signing keys, or realistic placeholder secrets.
- Never bypass the risk engine.
- Never let the frontend directly sign exchange requests.
- Never implement live trading without explicit config gates and tests proving those gates default to disabled.
- Never silently introduce taker orders.
- Never make withdrawals available.
- Never commit generated market data, model artifacts, checkpoints, local databases, logs, or cache output.

## Order Intent Pipeline

All order intents must go through:

1. Command validation.
2. Audit recording.
3. Risk checks.
4. Portfolio checks.
5. Execution checks.
6. Execution translation.
7. Exchange or paper-exchange submission.
8. Reconciliation.
9. Frontend update.

Do not skip stages for convenience. If a feature cannot use this path yet, keep it read-only or simulated.

## Hedge Mode

Hedge mode must represent independent `LONG` and `SHORT` books. Do not collapse long and short exposure into one net position when behavior depends on side-specific liquidation, margin, realized PnL, unrealized PnL, or reduce-only handling.

## Live Trading Gates

Live trading must remain disabled by default. Any future live-trading code must require explicit environment and configuration gates, mode checks, risk approval, portfolio approval, execution approval, audit records, and tests.

## Testing Expectations

- Always write tests for risk and execution behavior.
- Add regression tests for rejected commands, vetoes, mode gates, stale data handling, and hedge-mode behavior.
- Prefer deterministic tests over network-dependent tests.
- Do not connect to Binance in unit tests.

## Engineering Discipline

- Prefer small, reviewable commits.
- Update docs when changing architecture.
- Add TODO markers only when they are specific and actionable.
- Keep changes scoped to the requested behavior.
- Make configuration explicit and boring.
- Do not add trading strategy logic unless the task explicitly asks for it.
