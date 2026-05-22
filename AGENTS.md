# Contributor Instructions

These instructions apply to all AI coding agents and human contributors working in this repository. Treat this file as a safety contract for changes to AI-CryptoFutures-TCP.

For code review severity guidance, see [docs/code_review.md](docs/code_review.md).

For implementation sequencing, follow [docs/roadmap/developer_roadmap.md](docs/roadmap/developer_roadmap.md). Do not skip roadmap gates to reach strategy behavior, Binance testnet validation lanes, `LIVE` read-only capability, or gated live-trade behavior faster.

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
- Never hard-code permanent zero maker fees or assume fee promotions are permanent.
- Never make taker behavior the default; taker behavior must be explicit, gated, tested, and audited.
- Never make `ETHBTC` or `SYN_ETHBTC` executable without an explicit symbol-universe policy change, tests, and review.
- Never expose Binance testnet, `LIVE` read-only, or live-trade capability as separate top-level frontend modes; the frontend primary modes are `PAPER` and `LIVE`.
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

Frontend mode labels are intentionally simple: `PAPER` and `LIVE`. Internal services must still track `operator_mode`, `venue_target`, `credential_scope`, `trading_gate`, `autonomy_stage`, and `mlops_approval_state`. The two-mode UI must not hide or bypass live gates, risk checks, portfolio checks, execution checks, audit, or reconciliation.

MLOps approval states may indicate model or strategy readiness, but they must never bypass risk gates, live gates, portfolio checks, execution checks, audit, or reconciliation.

All order intents must move through command validation, audit recording, risk checks, portfolio checks, execution checks, execution translation, submission to an approved venue or simulator, reconciliation, and frontend update.

Strategies and models may propose actions, but their output is untrusted until backend validation, independent risk approval, portfolio approval, and execution approval have completed.

Frontend operator actions must be represented in the code-owned command catalog under `libs/schemas/commands.py`. Add or change catalog entries before building UI flows or backend handlers, and keep the catalog aligned with [docs/architecture/frontend_control_surface.md](docs/architecture/frontend_control_surface.md).

Symbol-universe behavior must follow [docs/market_data/three_asset_universe.md](docs/market_data/three_asset_universe.md), `configs/symbol_universe.yml`, and `libs/schemas/symbol_universe.py`. The initial executable set is `BTCUSDC` and `ETHUSDC`; `SYN_ETHBTC` is derived and direct `ETHBTC` is disabled reference-only data by default.

Binance-specific implementation must follow [docs/binance/binance_usdm_constraints.md](docs/binance/binance_usdm_constraints.md) and [docs/binance/fee_and_symbol_policy.md](docs/binance/fee_and_symbol_policy.md). Execution work must also follow [docs/execution/maker_microstructure_execution.md](docs/execution/maker_microstructure_execution.md).

## 4. Testing Rules

- Add tests for risk logic.
- Add tests for execution translation.
- Add tests for hedge-mode behavior.
- Add tests for live-trading gates.
- Add tests for config defaults.
- Add tests for dynamic fee assumptions and expected-edge calculations.
- Add tests for maker-first execution and taker leakage gates.
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
- Update Binance constraint and fee policy docs when changing venue assumptions.
- Update microstructure execution and research docs when changing maker-first or scalping-related assumptions.
- Document operator-mode, venue-target, credential-scope, trading-gate, autonomy-stage, MLOps-state, secret-handling, and order lifecycle changes before relying on them.

Documentation should describe buildable behavior, not vague intent. If a decision affects operator safety, exchange access, live-trading gates, or model governance, make it explicit.

Roadmap changes must keep [docs/roadmap/developer_roadmap.md](docs/roadmap/developer_roadmap.md) aligned with the Safety Spine, dynamic fee policy, frontend control surface, autonomy ladder, and live-trading gates.

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
