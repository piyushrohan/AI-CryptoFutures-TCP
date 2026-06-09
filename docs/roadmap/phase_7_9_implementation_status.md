# Phase 7-9 Implementation Status

This document tracks the local implementation status for roadmap Phases 7 through 9. It describes code that is intentionally validation-only and read-only where exchange-adjacent behavior is involved.

## Phase 7: Model Layer and Decision Records

Implemented locally:

- Typed model governance schemas for model registry entries, feature versions, evaluation summaries, model decision records, and recommendation previews.
- Local JSON-backed model governance store.
- API payloads for model registry, feature registry, evaluation summaries, decision records, and recommendation preview.
- Frontend model governance and decision-inspector panel.
- Enforcement helper proving a model recommendation cannot proceed to order-intent review unless a complete `ModelDecisionRecord` exists.

Still not implemented:

- Training worker.
- Real model serving.
- Model artifact registry.
- Model-driven execution.

## Phase 8: Binance Testnet Validation Lane

Implemented locally:

- Backend-only Binance USDⓈ-M Futures connector boundary.
- Validation-only request specifications for exchange information, commission rate, account information, position mode, user data stream lifecycle, and new-order payload shape.
- Testnet validation lane gates using `operator_mode=paper`, `venue_target=binance_testnet`, `credential_scope=trading`, and `autonomy_stage=testnet_auto`.
- Binance-shaped order-payload validation for maker-first, hedge-mode-aware payloads.
- No network calls, no request signing, and no order submission in CI or local default mode.

Still not implemented:

- Authenticated Binance testnet HTTP client.
- Request signing.
- User data stream connection.
- Testnet order submission.

## Phase 9: LIVE Read-only Account Visibility

Implemented locally:

- LIVE read-only account projection gated by `operator_mode=live`, `venue_target=binance_live`, `credential_scope=read_only`, and `trading_gate=locked`.
- Redacted credential metadata only; secret values are never returned.
- Audit record support for live read-only inspection.
- Explicit fail-closed live order rejection payload.
- Frontend LIVE read-only panel showing locked/read-only state and reconciliation status.

Still not implemented:

- Authenticated live Binance read-only HTTP client.
- Durable live reconciliation store.
- Live trade submission.

## Safety Notes

- The frontend still exposes only primary `PAPER` and `LIVE` modes.
- Binance testnet remains an internal validation lane.
- Live trading remains disabled by default and fail-closed.
- Browser code never receives Binance credentials and never signs Binance requests.
- Strategies and models still cannot directly call the exchange connector.
- Phase 10 live-trade research remains out of scope.

## Workstation Production Foundation

Implemented after the local Phase 7-9 wave:

- FastAPI `/api/v1` surface with Pydantic request contracts.
- Single-owner bearer-token authentication and CSRF checks for mutating routes.
- Command-ledger contract with idempotency keys and audit linkage.
- Postgres/Alembic schema scaffold for durable production state.
- Redacted env/macOS Keychain secret-provider contracts.
- Separate credential purposes for Binance testnet trading and Binance live
  read-only access.
- Backend-only Binance REST client foundation with HMAC signing, rate-limit
  header capture, request ID capture, and venue error classification.
- Monotonic reconciliation contracts for external order updates.

Still not implemented:

- Authenticated Binance testnet network workflows.
- User data stream websocket worker.
- Durable Postgres repositories replacing JSON/in-memory state.
- Testnet order submission.
- Authenticated `LIVE` read-only REST snapshots.
- Any live order submission.
