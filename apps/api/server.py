"""Minimal API gateway bootstrap for safe local startup."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from libs.config import RuntimeConfig, load_runtime_config
from libs.schemas import (
    CommandRequest,
    CommandType,
    PaperOrderIntent,
    control_surface_payload,
    symbol_universe_payload,
)
from services.backtesting import backtest_report_payload
from services.audit import InMemoryAuditRecorder
from services.market_data import (
    account_state_payload,
    exchange_state_payload,
    fee_policy_payload,
    replay_payload,
    symbol_metadata_payload,
)
from services.paper_exchange import InMemoryPaperExchange, default_paper_exchange
from services.risk import evaluate_command, risk_status_payload
from services.strategy import (
    StrategySessionManager,
    default_strategy_session_manager,
)


MAX_REQUEST_BYTES = 64_000
_AUDIT_RECORDER = InMemoryAuditRecorder()
_PAPER_EXCHANGE = default_paper_exchange()
_STRATEGY_MANAGER = default_strategy_session_manager()


def health_payload() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


def status_payload(config: RuntimeConfig | None = None) -> dict[str, Any]:
    runtime = config or load_runtime_config()
    return {
        "status": "ok",
        "service": "api",
        "runtime": runtime.to_status(),
        "placeholders": {
            "frontend": "expected",
            "api": "running",
            "database": "expected",
            "redis": "expected",
            "monitoring": "expected",
        },
    }


def audit_payload(recorder: InMemoryAuditRecorder | None = None) -> dict[str, Any]:
    selected_recorder = recorder or _AUDIT_RECORDER
    return {
        "status": "ok",
        "service": "audit",
        "records": selected_recorder.to_public_list(),
    }


def _audit_command_result(
    request: CommandRequest,
    result: Any,
    runtime: RuntimeConfig,
    recorder: InMemoryAuditRecorder,
) -> dict[str, Any]:
    decision = "accepted" if result.accepted else "rejected"
    return recorder.record_decision(
        command_type=request.command_type.value,
        actor_id=request.actor_id,
        decision=decision,
        reasons=list(result.reasons),
        payload=request.payload,
        runtime=runtime.to_status(),
    ).to_public_dict()


def validate_command_payload(
    body: dict[str, Any],
    *,
    config: RuntimeConfig | None = None,
    recorder: InMemoryAuditRecorder | None = None,
) -> dict[str, Any]:
    runtime = config or load_runtime_config()
    selected_recorder = recorder or _AUDIT_RECORDER
    request = CommandRequest.from_mapping(body)
    result = evaluate_command(runtime, request)
    record = _audit_command_result(request, result, runtime, selected_recorder)
    return {
        "status": "ok",
        "service": "api",
        "command": result.to_public_dict(),
        "audit_record": record,
        "execution": "not_performed",
    }


def _command_gate(
    command_type: CommandType,
    payload: dict[str, Any],
    *,
    config: RuntimeConfig | None = None,
    recorder: InMemoryAuditRecorder | None = None,
    fee_model_available: bool = True,
) -> tuple[RuntimeConfig, dict[str, Any], bool]:
    runtime = config or load_runtime_config()
    selected_recorder = recorder or _AUDIT_RECORDER
    request = CommandRequest(command_type, payload=payload)
    result = evaluate_command(
        runtime,
        request,
        fee_model_available=fee_model_available,
    )
    audit_record = _audit_command_result(
        request,
        result,
        runtime,
        selected_recorder,
    )
    return runtime, {
        "command": result.to_public_dict(),
        "audit_record": audit_record,
    }, result.accepted


def paper_preview_payload(
    body: dict[str, Any],
    *,
    exchange: InMemoryPaperExchange | None = None,
) -> dict[str, Any]:
    selected_exchange = exchange or _PAPER_EXCHANGE
    intent = PaperOrderIntent.from_mapping(body)
    preview = selected_exchange.preview_order(intent)
    return {
        "status": "ok",
        "service": "paper_exchange",
        "preview": preview.to_public_dict(),
        "execution": "paper_only",
    }


def paper_submit_payload(
    body: dict[str, Any],
    *,
    config: RuntimeConfig | None = None,
    exchange: InMemoryPaperExchange | None = None,
    recorder: InMemoryAuditRecorder | None = None,
) -> dict[str, Any]:
    selected_exchange = exchange or _PAPER_EXCHANGE
    _, gate, accepted = _command_gate(
        CommandType.SUBMIT_PAPER_ORDER,
        body,
        config=config,
        recorder=recorder,
        fee_model_available=True,
    )
    if not accepted:
        return {
            "status": "ok",
            "service": "paper_exchange",
            **gate,
            "paper_result": None,
            "execution": "not_performed",
        }
    result = selected_exchange.submit_order(PaperOrderIntent.from_mapping(body))
    return {
        "status": "ok",
        "service": "paper_exchange",
        **gate,
        "paper_result": result.to_public_dict(),
        "execution": "paper_only",
    }


def paper_reset_payload(
    body: dict[str, Any] | None = None,
    *,
    exchange: InMemoryPaperExchange | None = None,
) -> dict[str, Any]:
    selected_exchange = exchange or _PAPER_EXCHANGE
    selected_exchange.reset()
    return {
        "status": "ok",
        "service": "paper_exchange",
        "reset": True,
        "portfolio": selected_exchange.portfolio_payload(),
    }


def strategy_start_payload(
    body: dict[str, Any] | None = None,
    *,
    manager: StrategySessionManager | None = None,
) -> dict[str, Any]:
    selected_manager = manager or _STRATEGY_MANAGER
    family = (body or {}).get("family", "maker_microstructure")
    session = selected_manager.start_session(str(family))
    return {
        "status": "ok",
        "service": "strategy_sessions",
        "session": session.to_public_dict(),
        "recommendations": [
            item.to_public_dict() for item in selected_manager.recommendations()
        ],
    }


def strategy_pause_payload(
    body: dict[str, Any] | None = None,
    *,
    manager: StrategySessionManager | None = None,
) -> dict[str, Any]:
    selected_manager = manager or _STRATEGY_MANAGER
    session = selected_manager.pause_latest()
    return {
        "status": "ok",
        "service": "strategy_sessions",
        "session": session.to_public_dict() if session else None,
    }


def strategy_stop_payload(
    body: dict[str, Any] | None = None,
    *,
    manager: StrategySessionManager | None = None,
) -> dict[str, Any]:
    selected_manager = manager or _STRATEGY_MANAGER
    session = selected_manager.stop_latest()
    return {
        "status": "ok",
        "service": "strategy_sessions",
        "session": session.to_public_dict() if session else None,
    }


class ApiRequestHandler(BaseHTTPRequestHandler):
    server_version = "AI-CryptoFutures-TCP/0.1"

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(HTTPStatus.OK, health_payload())
            return
        if self.path == "/status":
            self._send_json(HTTPStatus.OK, status_payload())
            return
        if self.path == "/control-surface":
            self._send_json(HTTPStatus.OK, control_surface_payload())
            return
        if self.path == "/symbol-universe":
            self._send_json(HTTPStatus.OK, symbol_universe_payload())
            return
        if self.path == "/exchange-state":
            self._send_json(HTTPStatus.OK, exchange_state_payload())
            return
        if self.path == "/account-state":
            self._send_json(HTTPStatus.OK, account_state_payload())
            return
        if self.path == "/symbol-metadata":
            self._send_json(HTTPStatus.OK, symbol_metadata_payload())
            return
        if self.path == "/fee-policy":
            self._send_json(HTTPStatus.OK, fee_policy_payload())
            return
        if self.path == "/risk/status":
            self._send_json(HTTPStatus.OK, risk_status_payload(load_runtime_config()))
            return
        if self.path == "/audit/records":
            self._send_json(HTTPStatus.OK, audit_payload())
            return
        if self.path == "/paper":
            self._send_json(HTTPStatus.OK, _PAPER_EXCHANGE.summary_payload())
            return
        if self.path == "/paper/portfolio":
            self._send_json(HTTPStatus.OK, _PAPER_EXCHANGE.portfolio_payload())
            return
        if self.path == "/paper/orders":
            self._send_json(HTTPStatus.OK, _PAPER_EXCHANGE.orders_payload())
            return
        if self.path == "/paper/reconciliation":
            self._send_json(HTTPStatus.OK, _PAPER_EXCHANGE.reconciliation_payload())
            return
        if self.path == "/research/features":
            self._send_json(HTTPStatus.OK, replay_payload())
            return
        if self.path == "/backtests/report":
            self._send_json(HTTPStatus.OK, backtest_report_payload())
            return
        if self.path == "/strategy/sessions":
            self._send_json(HTTPStatus.OK, _STRATEGY_MANAGER.sessions_payload())
            return
        if self.path == "/strategy/recommendations":
            self._send_json(
                HTTPStatus.OK,
                _STRATEGY_MANAGER.recommendations_payload(),
            )
            return
        self._send_json(
            HTTPStatus.NOT_FOUND,
            {
                "status": "not_found",
                "available": [
                    "/health",
                    "/status",
                    "/control-surface",
                    "/symbol-universe",
                    "/exchange-state",
                    "/account-state",
                    "/symbol-metadata",
                    "/fee-policy",
                    "/risk/status",
                    "/audit/records",
                    "/paper",
                    "/paper/portfolio",
                    "/paper/orders",
                    "/paper/reconciliation",
                    "/research/features",
                    "/backtests/report",
                    "/strategy/sessions",
                    "/strategy/recommendations",
                ],
            },
        )

    def do_POST(self) -> None:
        if self.path == "/commands/validate":
            self._handle_command_validation()
            return
        if self.path == "/paper/preview":
            self._handle_json_payload(paper_preview_payload)
            return
        if self.path == "/paper/orders":
            self._handle_json_payload(paper_submit_payload)
            return
        if self.path == "/paper/reset":
            self._handle_json_payload(paper_reset_payload)
            return
        if self.path == "/paper/cancel":
            self._handle_json_payload(
                lambda payload: _PAPER_EXCHANGE.cancel_order(
                    str(payload.get("order_id", ""))
                )
            )
            return
        if self.path == "/paper/panic/halt":
            self._handle_json_payload(lambda payload: _PAPER_EXCHANGE.panic_halt())
            return
        if self.path == "/paper/panic/cancel":
            self._handle_json_payload(
                lambda payload: _PAPER_EXCHANGE.panic_cancel_open_orders()
            )
            return
        if self.path == "/paper/panic/flatten":
            self._handle_json_payload(
                lambda payload: _PAPER_EXCHANGE.panic_flatten_positions()
            )
            return
        if self.path == "/strategy/sessions/start":
            self._handle_json_payload(strategy_start_payload)
            return
        if self.path == "/strategy/sessions/pause":
            self._handle_json_payload(strategy_pause_payload)
            return
        if self.path == "/strategy/sessions/stop":
            self._handle_json_payload(strategy_stop_payload)
            return
        self._send_json(
            HTTPStatus.METHOD_NOT_ALLOWED,
            {
                "status": "method_not_allowed",
                "reason": "endpoint does not support this method",
            },
        )

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        # Keep local output quiet and avoid accidentally logging future request bodies.
        return

    def _handle_command_validation(self) -> None:
        self._handle_json_payload(validate_command_payload)

    def _handle_json_payload(self, handler: Any) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"status": "bad_request", "reason": "invalid content length"},
            )
            return
        if length > MAX_REQUEST_BYTES:
            self._send_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"status": "too_large", "reason": "request body is too large"},
            )
            return
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode("utf-8") if body else "{}")
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            response = handler(payload)
        except (json.JSONDecodeError, ValueError) as exc:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"status": "bad_request", "reason": str(exc)},
            )
            return
        self._send_json(HTTPStatus.OK, response)

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._send_cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str = "0.0.0.0", port: int | None = None) -> None:
    selected_port = port or int(os.environ.get("API_PORT", "8080"))
    server = ThreadingHTTPServer((host, selected_port), ApiRequestHandler)
    print(f"api listening on {host}:{selected_port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    run()
