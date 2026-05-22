"""Minimal API gateway bootstrap for safe local startup."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from libs.config import RuntimeConfig, load_runtime_config
from libs.schemas import CommandRequest, control_surface_payload, symbol_universe_payload
from services.audit import InMemoryAuditRecorder
from services.market_data import (
    account_state_payload,
    exchange_state_payload,
    fee_policy_payload,
    symbol_metadata_payload,
)
from services.risk import evaluate_command, risk_status_payload


MAX_REQUEST_BYTES = 64_000
_AUDIT_RECORDER = InMemoryAuditRecorder()


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
    decision = "accepted" if result.accepted else "rejected"
    record = selected_recorder.record_decision(
        command_type=request.command_type.value,
        actor_id=request.actor_id,
        decision=decision,
        reasons=list(result.reasons),
        payload=request.payload,
        runtime=runtime.to_status(),
    )
    return {
        "status": "ok",
        "service": "api",
        "command": result.to_public_dict(),
        "audit_record": record.to_public_dict(),
        "execution": "not_performed",
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
                ],
            },
        )

    def do_POST(self) -> None:
        if self.path == "/commands/validate":
            self._handle_command_validation()
            return
        self._send_json(
            HTTPStatus.METHOD_NOT_ALLOWED,
            {
                "status": "method_not_allowed",
                "reason": "only validation endpoints exist; execution is not implemented",
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
            response = validate_command_payload(payload)
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
