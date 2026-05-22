# Local Bootstrap

Local development should converge on a one-command startup that brings up the frontend-first control platform in a safe default state.

## Primary Command

```sh
make up
```

`make up` is the intended primary command for starting the local platform. The Phase 1 implementation starts a static frontend control shell, backend API, database, Redis, and monitoring placeholders needed for the operator to use the frontend as the main control surface.

## Startup Defaults

Local startup must default to:

- `APP_ENV=dev`.
- `operator_mode=paper`.
- `venue_target=internal_paper`.
- `credential_scope=none`.
- `trading_gate=locked`.
- `autonomy_stage=observe_only`.
- `live_trading_enabled=false`.
- No live exchange submission.
- No Binance credentials required.
- No browser access to exchange secrets.
- No frontend exchange signing.
- No strategy or model direct access to exchange connectors.

Observe mode should allow inspection, mocked or local state, documentation-linked controls, and safe development workflows. It must not place orders.

## Control Surface After Startup

After startup, the frontend should be the main entry point. Developers and operators should be able to inspect system health, operator mode, venue target, gate state, risk state, portfolio state, market data readiness, audit history, and available workflows from the browser.

Command-line tools may support development and maintenance, but they should not become the primary trading control path.

Phase 1 exposes the frontend at `http://localhost:3000` and the API at `http://localhost:8080`. The frontend displays mode/gate status, risk guardrails, the code-owned control-surface catalog, audit records, and disabled panic controls.

## Expected Local Services

The local stack should eventually include:

- Web frontend.
- API gateway.
- Postgres.
- Redis.
- Prometheus placeholder.
- Grafana placeholder.
- Optional local workers for paper exchange, training, evaluation, and backtesting.

## Acceptance Target

The first useful `make up` implementation should prove:

- Frontend starts.
- API starts.
- Database starts.
- Redis starts.
- Monitoring placeholders start.
- `operator_mode=paper` is active.
- `venue_target=internal_paper` is active.
- `credential_scope=none` is active.
- `trading_gate=locked` is active.
- `autonomy_stage=observe_only` is active.
- Live trading is disabled.
- No Binance credentials are required.
- The frontend is the main control surface after startup.

The initial repository may contain placeholders. The target behavior is a predictable local environment that starts safely and makes unsafe modes visibly unavailable.

## Safety Checks

The bootstrap flow should display or expose:

- Current operator mode, venue target, and gate state.
- Live-trading gate status.
- Secrets backend status without printing secret values.
- Risk-engine availability.
- Portfolio-engine availability.
- Execution-engine availability.
- Audit write availability.

If any safety dependency is unavailable, trading actions should remain blocked while read-only development workflows continue where possible.
