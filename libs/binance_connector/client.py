"""Backend-only Binance USD-M REST client foundation.

This module performs request signing only inside backend code and is written so
tests can inject an `httpx.Client` with a mock transport. It does not expose
secret values through public result metadata.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping
from urllib.parse import urlencode

import httpx

from libs.binance_connector.usdm import BinanceUsdmEnvironment, validate_backend_caller
from libs.security import CredentialBundle


class BinanceClientError(RuntimeError):
    """Raised when a backend Binance request cannot be built or sent."""


@dataclass(frozen=True)
class BinanceRestConfig:
    environment: BinanceUsdmEnvironment
    recv_window_ms: int = 5000
    timeout_seconds: Decimal = Decimal("10")

    @property
    def base_url(self) -> str:
        return self.environment.rest_base_url


@dataclass(frozen=True)
class BinanceRateLimitState:
    used_weight_1m: int | None = None
    order_count_10s: int | None = None
    order_count_1m: int | None = None

    def to_public_dict(self) -> dict[str, int | None]:
        return {
            "used_weight_1m": self.used_weight_1m,
            "order_count_10s": self.order_count_10s,
            "order_count_1m": self.order_count_1m,
        }


@dataclass(frozen=True)
class BinanceRestResult:
    status_code: int
    payload: Any
    request_id: str | None
    rate_limits: BinanceRateLimitState
    error_class: str | None = None

    def to_public_dict(self) -> dict[str, object]:
        return {
            "status_code": self.status_code,
            "payload": self.payload,
            "request_id": self.request_id,
            "rate_limits": self.rate_limits.to_public_dict(),
            "error_class": self.error_class,
        }


def _timestamp_ms() -> int:
    return int(time.time() * 1000)


def signed_query_string(
    params: Mapping[str, object],
    *,
    api_secret: str,
) -> str:
    """Return a Binance query string with HMAC SHA256 signature."""

    query = urlencode(
        [(key, str(value)) for key, value in sorted(params.items())],
        doseq=True,
    )
    signature = hmac.new(
        api_secret.encode("utf-8"),
        query.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{query}&signature={signature}"


class BinanceUsdmRestClient:
    def __init__(
        self,
        *,
        credentials: CredentialBundle,
        config: BinanceRestConfig,
        http_client: httpx.Client | None = None,
        caller: str = "backend_api",
    ) -> None:
        validate_backend_caller(caller)
        if not credentials.present:
            raise BinanceClientError("Binance credentials are missing")
        self._credentials = credentials
        self._config = config
        self._client = http_client or httpx.Client(
            base_url=config.base_url,
            timeout=float(config.timeout_seconds),
        )

    def signed_params(
        self,
        params: Mapping[str, object] | None = None,
        *,
        timestamp_ms: int | None = None,
    ) -> dict[str, object]:
        merged: dict[str, object] = dict(params or {})
        merged.setdefault("timestamp", timestamp_ms or _timestamp_ms())
        merged.setdefault("recvWindow", self._config.recv_window_ms)
        return merged

    def build_signed_query(
        self,
        params: Mapping[str, object] | None = None,
        *,
        timestamp_ms: int | None = None,
    ) -> str:
        return signed_query_string(
            self.signed_params(params, timestamp_ms=timestamp_ms),
            api_secret=self._credentials.api_secret,
        )

    def signed_request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
    ) -> BinanceRestResult:
        query = self.build_signed_query(params)
        headers = {"X-MBX-APIKEY": self._credentials.api_key}
        try:
            response = self._client.request(method, f"{path}?{query}", headers=headers)
        except httpx.HTTPError as exc:
            raise BinanceClientError("Binance request failed") from exc
        return self._result_from_response(response)

    def public_request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
    ) -> BinanceRestResult:
        try:
            response = self._client.request(method, path, params=dict(params or {}))
        except httpx.HTTPError as exc:
            raise BinanceClientError("Binance request failed") from exc
        return self._result_from_response(response)

    @staticmethod
    def _result_from_response(response: httpx.Response) -> BinanceRestResult:
        error_class = None if response.status_code < 400 else _error_class(response)
        try:
            payload: Any = response.json()
        except ValueError:
            payload = {"text": response.text}
        return BinanceRestResult(
            status_code=response.status_code,
            payload=payload,
            request_id=response.headers.get("x-mbx-uuid")
            or response.headers.get("x-response-id"),
            rate_limits=BinanceRateLimitState(
                used_weight_1m=_int_header(response, "x-mbx-used-weight-1m"),
                order_count_10s=_int_header(response, "x-mbx-order-count-10s"),
                order_count_1m=_int_header(response, "x-mbx-order-count-1m"),
            ),
            error_class=error_class,
        )


def _int_header(response: httpx.Response, name: str) -> int | None:
    value = response.headers.get(name)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _error_class(response: httpx.Response) -> str:
    if response.status_code in {401, 403}:
        return "auth_error"
    if response.status_code == 429:
        return "rate_limited"
    if response.status_code >= 500:
        return "venue_server_error"
    return "venue_rejection"
