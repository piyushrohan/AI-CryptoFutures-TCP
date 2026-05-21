"""Minimal API gateway bootstrap for safe local startup."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from libs.config import RuntimeConfig, load_runtime_config


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


class ApiRequestHandler(BaseHTTPRequestHandler):
    server_version = "AI-CryptoFutures-TCP/0.1"

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(HTTPStatus.OK, health_payload())
            return
        if self.path == "/status":
            self._send_json(HTTPStatus.OK, status_payload())
            return
        self._send_json(
            HTTPStatus.NOT_FOUND,
            {"status": "not_found", "available": ["/health", "/status"]},
        )

    def do_POST(self) -> None:
        self._send_json(
            HTTPStatus.METHOD_NOT_ALLOWED,
            {"status": "method_not_allowed", "reason": "no command endpoints exist yet"},
        )

    def log_message(self, format: str, *args: object) -> None:
        # Keep local output quiet and avoid accidentally logging future request bodies.
        return

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
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
