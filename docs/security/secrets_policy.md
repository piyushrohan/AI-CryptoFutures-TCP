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

Any future Binance integration must keep signing in backend infrastructure, enforce operating modes, and prove through tests that live-trading permissions are disabled by default.
