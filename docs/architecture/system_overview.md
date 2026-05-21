# System Overview

AI-CryptoFutures-TCP is intended to be a frontend-first Trading Control Platform rather than an autonomous trading bot. The frontend exposes only `PAPER` and `LIVE` as primary operator modes while acting as the control tower for observe-only session state, paper workflows, internal testnet validation lanes, `LIVE` read-only inspection, live-trade approval, training, evaluation, backtesting, strategy sessions, model registry workflows, panic controls, audit review, and model decision inspection.

## Target Flow

```text
Frontend Control Plane
  -> Backend API Gateway
  -> Risk / Portfolio / Strategy / Execution Core
  -> Paper Exchange / Binance USDⓈ-M Futures Testnet / Future Binance Live
```

## Responsibilities

The frontend control plane presents account state, market state, model decisions, operator controls, approvals, training and evaluation workflows, backtesting, strategy sessions, panic actions, and audit visibility. It never receives exchange secrets and never signs exchange requests.

The backend API gateway authenticates users, validates commands, enforces operator-mode, venue-target, credential-scope, trading-gate, autonomy-stage, and MLOps-state constraints, writes audit records, and routes requests to domain services.

The risk, portfolio, strategy, and execution core validates every order intent before it can reach an exchange or simulator. The risk engine can veto any command. Portfolio checks verify exposure, margin, hedge-mode books, funding exposure, liquidation buffer, and command consistency. Execution checks translate approved intents into venue-specific requests.

Paper exchange, Binance USDⓈ-M Futures testnet, and future Binance live integrations are venue boundaries. Live trading remains disabled by default and must be gated by explicit configuration and approval.

Execution should be maker-first by default. Taker behavior must be explicit, gated, tested, and audited. Fee assumptions must be dynamic, configurable, audited, and included in expected-edge calculations.

## Initial Repository Scope

This skeleton defines the target boundaries only. It intentionally does not implement strategy logic, Binance connectivity, live trading, or model-serving behavior.
