# AI-CryptoFutures-TCP

AI-CryptoFutures-TCP is the initial skeleton for an AI crypto futures Trading Control Platform focused first on Binance USDⓈ-M Futures.

TCP means Trading Control Platform. This project is intended to become a frontend-first control plane for observing markets, issuing manual trading commands, running paper and testnet workflows, managing training, evaluation, backtesting, strategy sessions, model deployment, and governing eventual live trading behind strict controls. It is not just a bot.

This repository currently contains guardrails, documentation, configuration placeholders, and service boundaries only. It does not contain trading strategy logic, Binance connectivity, live trading code, or real credentials.

## Safety Model

- Frontend controls everything.
- Backend validates everything.
- Risk engine can veto everything.
- Secrets never touch the frontend.

Every future order intent must pass through command validation, audit recording, risk checks, portfolio checks, execution checks, and reconciliation before it is reflected back to the frontend.

The initial preferred research universe is USDC-quoted Binance USDⓈ-M Futures perpetual pairs, such as `BTCUSDC` and `ETHUSDC`, subject to current dynamic fee, liquidity, funding, and risk policy. Fee assumptions must be configurable and audited; permanent zero maker fees must not be hard-coded.

Execution should be maker-first by default. Taker behavior must be explicit, gated, tested, and audited.

## Operating Modes

The intended operating modes are:

- `observe`: view-only workflows with no order placement.
- `paper`: simulated exchange workflows using a paper exchange.
- `testnet`: exchange testnet workflows only.
- `live-readonly`: live account visibility without trade permission.
- `live-trade`: live trade capability behind explicit gates.

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

The implementation sequence is defined in [docs/roadmap/developer_roadmap.md](docs/roadmap/developer_roadmap.md). It is phase-gated rather than date-based, with frontend control mapping first, Safety Spine before strategy, observe plus paper as the MVP, Binance testnet after paper, live-readonly before any live-trade path, and Portfolio Margin treated as later research.

## Development Status

This is a professional repository skeleton. Implementation code will be added incrementally only after the relevant control, risk, testing, and documentation expectations are clear.
