# System Overview

AI-CryptoFutures-TCP is intended to be a frontend-first Trading Control Platform rather than an autonomous trading bot.

## Target Flow

```text
Frontend Control Plane
  -> Backend API Gateway
  -> Risk / Portfolio / Strategy / Execution Core
  -> Binance Testnet / Binance Live / Paper Exchange
```

## Responsibilities

The frontend control plane presents account state, market state, model decisions, operator controls, approvals, panic actions, and audit visibility. It never receives exchange secrets and never signs exchange requests.

The backend API gateway authenticates users, validates commands, enforces operating mode, writes audit records, and routes requests to domain services.

The risk, portfolio, strategy, and execution core validates every order intent before it can reach an exchange or simulator. The risk engine can veto any command. Portfolio checks verify exposure, margin, hedge-mode books, and command consistency. Execution checks translate approved intents into venue-specific requests.

Paper exchange, Binance testnet, and future Binance live integrations are venue boundaries. Live trading remains disabled by default and must be gated by explicit configuration and approval.

## Initial Repository Scope

This skeleton defines the target boundaries only. It intentionally does not implement strategy logic, Binance connectivity, live trading, or model-serving behavior.
