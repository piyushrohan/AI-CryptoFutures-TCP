# Security Policy

AI-CryptoFutures-TCP is designed around strict separation of control, validation, execution, and secret handling.

## Core Principles

- Secrets are never committed.
- Exchange secrets never reach the frontend.
- Backend services are responsible for signing any future exchange requests.
- Restricted API keys must be used for exchange access.
- Withdrawals must never be enabled.
- Read-only and trading credentials must be separate.
- Live trading must remain disabled by default.

## Reporting Security Issues

This is a private repository. Report suspected vulnerabilities, leaked credentials, unsafe defaults, or risk-engine bypasses directly to the repository owner through the approved private communication channel.

## Current Scope

The current repository state is a skeleton only. It contains no live exchange connectivity, no trading strategy logic, and no real secrets.
