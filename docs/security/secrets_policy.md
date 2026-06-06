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

## Exchange Access

Any future Binance integration must keep signing in backend infrastructure, enforce operator-mode, venue-target, credential-scope, trading-gate, autonomy-stage, and MLOps-state constraints, and prove through tests that live-trading permissions are disabled by default.

The current Binance USDⓈ-M Futures boundary is validation-only. It may report whether backend credentials are present, but it must only expose redacted credential metadata such as `api_key_present`, `api_secret_present`, and `secrets_redacted`. Secret values must never be returned to the frontend, audit records, logs, tests, or documentation.
