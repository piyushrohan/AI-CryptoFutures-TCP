# Secrets Policy

Secrets are operational material, not source code. They must never be committed to this repository.

## Rules

- The frontend never receives exchange secrets.
- Backend services sign future exchange requests.
- Secrets are never committed.
- Restricted API keys must be used.
- IP allowlisting should be used where possible.
- Read-only and trading keys must be separate.
- Withdrawals must never be enabled.

## Configuration

Use `.env.example` to document expected environment variable names only. Keep real values in an approved secret manager or local developer environment outside version control.

For the first single-owner workstation production target, the backend supports:

- `SECRETS_BACKEND=macos_keychain` for macOS Keychain access.
- `SECRETS_BACKEND=env` for development and tests.
- Separate Binance testnet trading credentials:
  `BINANCE_TESTNET_API_KEY` and `BINANCE_TESTNET_API_SECRET`.
- Separate Binance live read-only credentials:
  `BINANCE_LIVE_READONLY_API_KEY` and
  `BINANCE_LIVE_READONLY_API_SECRET`.

The API may expose only redacted credential metadata, such as whether a key and
secret are present for a given purpose. It must not expose the actual values.

## Exchange Access

Any future Binance integration must keep signing in backend infrastructure, enforce operator-mode, venue-target, credential-scope, trading-gate, autonomy-stage, and MLOps-state constraints, and prove through tests that live-trading permissions are disabled by default.

The current Binance USDⓈ-M Futures boundary includes validation-only payload
translation and a backend-only REST client foundation that can build signed
requests when supplied backend credentials. Production network submission and
live order placement remain disabled until later phases implement authenticated
request workflows, reconciliation, risk gates, and operational runbooks. Secret
values must never be returned to the frontend, audit records, logs, tests, or
documentation.
