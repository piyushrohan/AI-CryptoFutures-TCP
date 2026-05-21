# Local Bootstrap

Local development should converge on a one-command startup that brings up the frontend-first control platform in a safe default state.

## Primary Command

```sh
make up
```

`make up` is the intended primary command for starting the local platform once implementation exists. It should start the frontend, backend API, database, Redis, and monitoring placeholders needed for the operator to use the frontend as the main control surface.

## Startup Defaults

Local startup must default to:

- `APP_ENV=dev`.
- `TRADING_MODE=observe`.
- `LIVE_TRADING_ENABLED=false`.
- No live exchange submission.
- No Binance credentials required.
- No browser access to exchange secrets.
- No frontend exchange signing.
- No strategy or model direct access to exchange connectors.

Observe mode should allow inspection, mocked or local state, documentation-linked controls, and safe development workflows. It must not place orders.

## Control Surface After Startup

After startup, the frontend should be the main entry point. Developers and operators should be able to inspect system health, operating mode, risk state, portfolio state, market data readiness, audit history, and available workflows from the browser.

Command-line tools may support development and maintenance, but they should not become the primary trading control path.

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
- Observe mode is active.
- Live trading is disabled.
- No Binance credentials are required.
- The frontend is the main control surface after startup.

The initial repository may contain placeholders. The target behavior is a predictable local environment that starts safely and makes unsafe modes visibly unavailable.

## Safety Checks

The bootstrap flow should display or expose:

- Current operating mode.
- Live-trading gate status.
- Secrets backend status without printing secret values.
- Risk-engine availability.
- Portfolio-engine availability.
- Execution-engine availability.
- Audit write availability.

If any safety dependency is unavailable, trading actions should remain blocked while read-only development workflows continue where possible.
