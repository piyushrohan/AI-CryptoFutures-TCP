"""FastAPI production API surface.

The routes are mounted under `/api/v1` and reuse the existing payload builders
while adding typed ingress, single-owner auth, CSRF checks, and command-ledger
metadata. Legacy stdlib helpers remain importable for the existing test suite.
"""

from __future__ import annotations

from typing import Any

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request

from apps.api.contracts import (
    BacktestRunRequest,
    CommandValidationRequest,
    OrderIdRequest,
    PaperOrderRequest,
    RecommendationPreviewRequest,
    StrategySessionRequest,
)
from apps.api import server as payloads
from libs.security import (
    AuthError,
    CredentialPurpose,
    OperatorIdentity,
    SingleOwnerAuthConfig,
    secret_provider_from_env,
)
from services.audit import InMemoryCommandLedger
from services.storage import PostgresSettings


def create_app(
    *,
    auth_config: SingleOwnerAuthConfig | None = None,
    command_ledger: InMemoryCommandLedger | None = None,
) -> FastAPI:
    app = FastAPI(
        title="AI-CryptoFutures-TCP API",
        version="0.2.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    selected_auth = auth_config or SingleOwnerAuthConfig.from_env()
    selected_ledger = command_ledger or InMemoryCommandLedger()

    def require_operator(
        request: Request,
        authorization: str | None = Header(default=None),
        x_tcp_csrf_token: str | None = Header(default=None),
    ) -> OperatorIdentity:
        try:
            identity = selected_auth.authenticate_bearer(authorization)
            selected_auth.validate_csrf(request.method, x_tcp_csrf_token)
        except AuthError as exc:
            status_code = 503 if "not configured" in str(exc) else 401
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc
        return identity

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return payloads.health_payload()

    @app.get("/api/v1/auth/status")
    def auth_status() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "auth",
            "auth": selected_auth.to_public_dict(),
        }

    @app.get("/api/v1/status")
    def status(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, Any]:
        return payloads.status_payload()

    @app.get("/api/v1/ops/status")
    def ops_status(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        provider = secret_provider_from_env()
        return {
            "status": "ok",
            "service": "ops",
            "auth": selected_auth.to_public_dict(),
            "storage": PostgresSettings.from_env().to_public_dict(),
            "secrets": {
                "testnet_trading": provider.public_metadata(
                    CredentialPurpose.BINANCE_TESTNET_TRADING
                ),
                "live_readonly": provider.public_metadata(
                    CredentialPurpose.BINANCE_LIVE_READONLY
                ),
            },
            "binance": {
                "network_calls": "not_performed",
                "request_specs": payloads.testnet_validation_payload()[
                    "request_specs"
                ],
            },
        }

    @app.get("/api/v1/control-surface")
    def control_surface(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.control_surface_payload()

    @app.get("/api/v1/symbol-universe")
    def symbol_universe(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.symbol_universe_payload()

    @app.get("/api/v1/exchange-state")
    def exchange_state(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, Any]:
        return payloads.exchange_state_payload()

    @app.get("/api/v1/account-state")
    def account_state(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, Any]:
        return payloads.account_state_payload()

    @app.get("/api/v1/symbol-metadata")
    def symbol_metadata(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, Any]:
        return payloads.symbol_metadata_payload()

    @app.get("/api/v1/fee-policy")
    def fee_policy(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, Any]:
        return payloads.fee_policy_payload()

    @app.get("/api/v1/risk/status")
    def risk_status(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.risk_status_payload(payloads.load_runtime_config())

    @app.get("/api/v1/audit/records")
    def audit_records(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, Any]:
        return payloads.audit_payload()

    @app.get("/api/v1/audit/commands")
    def audit_commands(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "command_ledger",
            "commands": selected_ledger.to_public_list(),
        }

    @app.post("/api/v1/commands/validate")
    def validate_command(
        body: CommandValidationRequest,
        identity: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, Any]:
        runtime = payloads.load_runtime_config()
        request_body = {
            "command_type": body.command_type,
            "actor_id": body.actor_id or identity.actor_id,
            "payload": body.payload,
        }
        try:
            ledger_entry = selected_ledger.record_received(
                command_type=body.command_type,
                actor_id=body.actor_id or identity.actor_id,
                payload=body.payload,
                runtime=runtime.to_status(),
                idempotency_key=body.idempotency_key,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        response = payloads.validate_command_payload(request_body, config=runtime)
        updated = selected_ledger.record_decision(
            ledger_entry.command_id,
            accepted=bool(response["command"]["accepted"]),
            audit_record_id=response["audit_record"]["record_id"],
        )
        response["command_ledger"] = updated.to_public_dict()
        return response

    @app.get("/api/v1/paper")
    def paper_summary(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, Any]:
        return payloads._PAPER_EXCHANGE.summary_payload()

    @app.get("/api/v1/paper/portfolio")
    def paper_portfolio(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads._PAPER_EXCHANGE.portfolio_payload()

    @app.get("/api/v1/paper/orders")
    def paper_orders(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads._PAPER_EXCHANGE.orders_payload()

    @app.get("/api/v1/paper/reconciliation")
    def paper_reconciliation(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads._PAPER_EXCHANGE.reconciliation_payload()

    @app.post("/api/v1/paper/preview")
    def paper_preview(
        body: PaperOrderRequest,
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, Any]:
        return payloads.paper_preview_payload(body.model_dump())

    @app.post("/api/v1/paper/orders")
    def paper_submit(
        body: PaperOrderRequest,
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, Any]:
        return payloads.paper_submit_payload(body.model_dump())

    @app.post("/api/v1/paper/reset")
    def paper_reset(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, Any]:
        return payloads.paper_reset_payload()

    @app.post("/api/v1/paper/cancel")
    def paper_cancel(
        body: OrderIdRequest,
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads._PAPER_EXCHANGE.cancel_order(body.order_id)

    @app.post("/api/v1/paper/expire")
    def paper_expire(
        body: OrderIdRequest,
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads._PAPER_EXCHANGE.expire_order(body.order_id)

    @app.post("/api/v1/paper/process")
    def paper_process(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.paper_process_payload()

    @app.post("/api/v1/paper/panic/halt")
    def paper_panic_halt(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads._PAPER_EXCHANGE.panic_halt()

    @app.post("/api/v1/paper/panic/cancel")
    def paper_panic_cancel(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads._PAPER_EXCHANGE.panic_cancel_open_orders()

    @app.post("/api/v1/paper/panic/flatten")
    def paper_panic_flatten(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads._PAPER_EXCHANGE.panic_flatten_positions()

    @app.get("/api/v1/research/features")
    def research_features(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.replay_payload()

    @app.get("/api/v1/backtests/report")
    def backtest_report(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.backtest_report_payload()

    @app.post("/api/v1/backtests/run")
    def backtest_run(
        body: BacktestRunRequest,
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.backtest_run_payload(body.model_dump())

    @app.get("/api/v1/strategy/sessions")
    def strategy_sessions(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads._STRATEGY_MANAGER.sessions_payload()

    @app.get("/api/v1/strategy/recommendations")
    def strategy_recommendations(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads._STRATEGY_MANAGER.recommendations_payload()

    @app.post("/api/v1/strategy/sessions/start")
    def strategy_start(
        body: StrategySessionRequest,
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.strategy_start_payload(body.model_dump())

    @app.post("/api/v1/strategy/sessions/pause")
    def strategy_pause(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.strategy_pause_payload()

    @app.post("/api/v1/strategy/sessions/stop")
    def strategy_stop(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.strategy_stop_payload()

    @app.get("/api/v1/models/registry")
    def models_registry(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.model_registry_payload()

    @app.get("/api/v1/models/features")
    def models_features(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.feature_registry_payload()

    @app.get("/api/v1/models/evaluations")
    def models_evaluations(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.evaluation_results_payload()

    @app.get("/api/v1/models/decisions")
    def models_decisions(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.model_decision_records_payload()

    @app.post("/api/v1/models/recommendation-preview")
    def models_recommendation_preview(
        body: RecommendationPreviewRequest,
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.recommendation_preview_payload(body.model_dump())

    @app.get("/api/v1/binance/testnet/validation")
    def testnet_validation(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.testnet_validation_payload(payloads.load_runtime_config())

    @app.post("/api/v1/binance/testnet/order/validate")
    def testnet_order_validate(
        body: dict[str, Any] = Body(default_factory=dict),
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.testnet_order_validation_payload(
            body,
            config=payloads.load_runtime_config(),
        )

    @app.get("/api/v1/live/readonly")
    def live_readonly(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.live_readonly_account_payload(
            payloads.load_runtime_config(),
            recorder=payloads._AUDIT_RECORDER,
        )

    @app.post("/api/v1/live/orders")
    def live_orders(
        _: OperatorIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        return payloads.live_order_rejection_payload(payloads.load_runtime_config())

    return app


app = create_app()
