# Workstation Production Readiness

This document tracks the first production-ready target for a single-owner local
workstation release. The release target is real Binance USD-M Futures testnet
connectivity and real Binance USD-M Futures `LIVE` read-only visibility. It
does not include live order submission.

## Implemented Foundation

- FastAPI production API surface under `/api/v1`.
- Single-owner bearer token authentication for protected API routes.
- CSRF token requirement for mutating API routes.
- Pydantic request models for command validation, paper orders, strategy
  session controls, backtest runs, and model recommendation previews.
- Idempotent command ledger contract with payload fingerprints and audit record
  linkage.
- Redacted secret-provider abstraction with env and macOS Keychain providers.
- Separate credential purposes for Binance testnet trading and Binance live
  read-only access.
- Backend-only Binance USD-M REST client foundation with HMAC signing,
  recvWindow/timestamp handling, request ID capture, rate-limit header capture,
  and venue error classification.
- Monotonic order-reconciliation contracts for Binance order updates.
- Postgres/Alembic production schema scaffold for audit, commands, snapshots,
  paper lifecycle, reconciliation, model metadata, strategy sessions, and
  runtime config versions.

## Still Required Before Testnet Trading

- Postgres repository implementations that replace JSON and in-memory state as
  the source of truth.
- Authenticated Binance testnet REST calls for exchange info, position mode,
  account state, open orders, commission rate, listen-key lifecycle, and order
  submission.
- User data stream websocket worker with reconnect, keepalive, duplicate-event
  handling, REST backfill, and durable reconciliation writes.
- Testnet order submission endpoint that only runs after command validation,
  audit, risk, portfolio checks, execution translation, and reconciliation
  setup pass.
- Dynamic symbol metadata and fee snapshots sourced from Binance testnet.
- Rate-limit and API-error kill switches connected to risk state.

## Still Required Before LIVE Read-only

- Backend-only Binance live read-only REST calls for account, position mode,
  balances, positions, open orders, and commission rates.
- Live read-only snapshot persistence and reconciliation comparison.
- Separate read-only credential verification and operator-visible credential
  metadata.
- Tests proving live read-only credentials cannot submit, cancel, replace, or
  sign live trading requests.

## Explicitly Out Of Scope

- Live order submission.
- Autonomous live trading.
- Browser access to Binance credentials.
- Browser request signing.
- Withdrawals.
- Executable `ETHBTC` or `SYN_ETHBTC`.
- Strategy or model direct access to exchange connectors.

## Local Operator Setup

Set local owner API tokens outside version control:

```sh
export TCP_ADMIN_TOKEN="<local owner API token>"
export TCP_CSRF_TOKEN="<local CSRF token>"
```

Store Binance workstation credentials in macOS Keychain when using
`SECRETS_BACKEND=macos_keychain`:

```sh
security add-generic-password -s AI-CryptoFutures-TCP:binance_testnet_trading -a api_key -w "<testnet api key>"
security add-generic-password -s AI-CryptoFutures-TCP:binance_testnet_trading -a api_secret -w "<testnet api secret>"
security add-generic-password -s AI-CryptoFutures-TCP:binance_live_readonly -a api_key -w "<live read-only api key>"
security add-generic-password -s AI-CryptoFutures-TCP:binance_live_readonly -a api_secret -w "<live read-only api secret>"
```

For development and tests, env fallback names are:

- `BINANCE_TESTNET_API_KEY`
- `BINANCE_TESTNET_API_SECRET`
- `BINANCE_LIVE_READONLY_API_KEY`
- `BINANCE_LIVE_READONLY_API_SECRET`

These values must remain backend-only.

## Backup And Restore

For local Postgres backups:

```sh
pg_dump "$DATABASE_URL" > tcp_workstation_backup.sql
```

For restore:

```sh
psql "$DATABASE_URL" < tcp_workstation_backup.sql
```

For Keychain recovery, re-add credentials with the `security
add-generic-password` commands above. Do not export exchange credentials into
repository files, frontend code, logs, audit payloads, or test fixtures.
