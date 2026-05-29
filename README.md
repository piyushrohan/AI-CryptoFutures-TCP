# AI-CryptoFutures-TCP

AI-CryptoFutures-TCP is the initial skeleton for an AI crypto futures Trading Control Platform focused first on Binance USDⓈ-M Futures.

TCP means Trading Control Platform. This project is intended to become a frontend-first control plane for observing markets, issuing manual trading commands, running paper workflows, running internal Binance testnet validation lanes, managing training, evaluation, backtesting, strategy sessions, model deployment, and governing eventual live trading behind strict controls. It is not just a bot.

This repository currently contains guardrails, documentation, configuration placeholders, and service boundaries only. It does not contain trading strategy logic, Binance connectivity, live trading code, or real credentials.

## Safety Model

- Frontend controls everything.
- Backend validates everything.
- Risk engine can veto everything.
- Secrets never touch the frontend.

Every future order intent must pass through command validation, audit recording, risk checks, portfolio checks, execution checks, and reconciliation before it is reflected back to the frontend.

The initial preferred research universe is USDC-quoted Binance USDⓈ-M Futures perpetual pairs, such as `BTCUSDC` and `ETHUSDC`, subject to current dynamic fee, liquidity, funding, and risk policy. Fee assumptions must be configurable and audited; permanent zero maker fees must not be hard-coded.

The first BTC/ETH focus treats `BTCUSDC` and `ETHUSDC` as executable instruments, `SYN_ETHBTC` as a derived non-executable series, and direct `ETHBTC` as disabled reference-only data unless a future policy explicitly promotes it.

Execution should be maker-first by default. Taker behavior must be explicit, gated, tested, and audited.

## Operator Mode, Venue Target, Gates, and Lanes

The frontend should expose only two primary operator modes:

- `PAPER`: the first full user-facing mode, backed initially by the internal paper venue.
- `LIVE`: introduced later, first as read-only account visibility.

Internal state remains more precise than the UI label:

- `operator_mode`: `paper` or `live`.
- `venue_target`: `internal_paper`, `binance_testnet`, or `binance_live`.
- `credential_scope`: `none`, `read_only`, or `trading`.
- `trading_gate`: `locked`, `approval_required`, `tiny_live`, `armed`, or `halted`.
- `autonomy_stage`: `observe_only`, `suggest_only`, `human_approval`, `paper_auto`, `testnet_auto`, `tiny_live_auto`, or `scaled_live_auto`.
- `mlops_approval_state`: `research_candidate`, `backtest_approved`, `paper_approved`, `testnet_validated`, `live_readonly_validated`, `live_trade_candidate`, or `live_trade_approved`.

Observe is an autonomy stage or session state, not a top-level operator mode. Binance testnet is an internal validation lane, not a top-level operator mode. `LIVE` read-only is `LIVE` with `credential_scope=read_only` and `trading_gate=locked`. Live-trade capability is `LIVE` with trading credentials, explicit live trading gates, a live autonomy stage, and `mlops_approval_state=live_trade_approved`.

Live trading is disabled by default. Any future live trading implementation must require explicit configuration gates, tests, review, and human approval.

## Secrets

Secrets must never be committed. Keep API keys, signing keys, JWT secrets, database passwords, and service credentials out of the repository. Use `.env.example` only as a list of expected variable names with blank or fake non-secret values.

Exchange secrets must remain backend-only. The frontend must never receive exchange API keys or sign exchange requests.

## Repository Map

- `apps/web/`: frontend control plane.
- `apps/api/`: backend API gateway.
- `services/`: domain services for market data, execution, risk, portfolio, strategy, model serving, training, backtesting, paper exchange, and audit.
- `libs/`: shared schemas, configuration, logging, security helpers, and future exchange connector boundaries.
- `configs/`: environment-specific configuration templates.
- `docs/`: architecture, risk, execution, MLOps, security, and Binance notes.
- `tests/`: unit, integration, replay, risk, and execution test suites.
- `infra/`: local Docker, Prometheus, and Grafana scaffolding.

## Developer Roadmap

The implementation sequence is defined in [docs/roadmap/developer_roadmap.md](docs/roadmap/developer_roadmap.md). It is phase-gated rather than date-based, with frontend control mapping first, Safety Spine before strategy, `PAPER` as the first full user-facing mode, Binance testnet as an internal validation lane after paper, `LIVE` introduced first with read-only credentials, and Portfolio Margin treated as later research.

## Local Bootstrap

Use `make up` to start the local development stack. It starts a static frontend control shell at `http://localhost:3000`, an API bootstrap at `http://localhost:8080`, database, Redis, and monitoring placeholders with `operator_mode=paper`, `venue_target=internal_paper`, `credential_scope=none`, `trading_gate=locked`, `autonomy_stage=observe_only`, and live trading disabled. Binance credentials are not required for local bootstrap.

The API exposes read-only safety and Phase 2 truth-model endpoints plus command validation only:

- `GET /health`
- `GET /status`
- `GET /control-surface`
- `GET /symbol-universe`
- `GET /exchange-state`
- `GET /account-state`
- `GET /symbol-metadata`
- `GET /fee-policy`
- `GET /risk/status`
- `GET /audit/records`
- `GET /models/registry`
- `GET /models/features`
- `GET /models/evaluations`
- `GET /models/decisions`
- `GET /binance/testnet/validation`
- `GET /live/readonly`
- `POST /commands/validate`
- `POST /models/recommendation-preview`
- `POST /binance/testnet/order/validate`
- `POST /live/orders`

`POST /commands/validate` records an audit decision and performs no execution. Trading-affecting commands are rejected in `observe_only`, strategy/session commands require a current fee model, and live trading remains fail-closed. Testnet order validation builds Binance-shaped payloads only; it does not sign or submit orders. `POST /live/orders` is an explicit fail-closed rejection in this phase.

## Development Status

Phase 0 and Phase 1 bootstrap code define the control-surface contract, safe runtime defaults, command validation scaffolding, audit scaffolding, risk veto scaffolding, and CI baseline. Phase 2 adds deterministic local/mock account state, symbol metadata, fee policy, freshness checks, and read-only inspectors. Phases 3 through 6 add deterministic local paper trading, portfolio/risk hardening, synthetic microstructure replay/backtests, and paper-only strategy sessions. Phases 7 through 9 add local model decision records, validation-only Binance USDⓈ-M Futures testnet lane scaffolding, and gated `LIVE` read-only projection. Real Binance connectivity, request signing, testnet order submission, model-driven execution, and live trading are not implemented.
