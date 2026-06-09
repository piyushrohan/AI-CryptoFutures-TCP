"""Validation-only Binance USDⓈ-M Futures connector boundary.

The boundary models request shapes and Binance-specific order fields for tests
and review. It never opens sockets, signs browser requests, stores credentials,
or submits live/testnet orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from libs.config import CredentialScope, RuntimeConfig, VenueTarget
from libs.schemas import (
    BookSide,
    OrderSide,
    PaperOrderIntent,
    SymbolMetadata,
    TimeInForce,
    decimal_str,
)


class ConnectorBoundaryError(ValueError):
    """Raised when a caller attempts to cross the backend-only boundary unsafely."""


class BinanceUsdmEnvironment(str, Enum):
    TESTNET = "testnet"
    LIVE = "live"

    @property
    def rest_base_url(self) -> str:
        if self == BinanceUsdmEnvironment.TESTNET:
            return "https://testnet.binancefuture.com"
        return "https://fapi.binance.com"


@dataclass(frozen=True)
class BinanceRequestSpec:
    name: str
    method: str
    path: str
    signed: bool
    source_doc: str

    def to_public_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "method": self.method,
            "path": self.path,
            "signed": self.signed,
            "source_doc": self.source_doc,
        }


@dataclass(frozen=True)
class BinanceUsdmOrderPayload:
    symbol: str
    side: OrderSide
    position_side: BookSide
    order_type: str
    time_in_force: TimeInForce
    quantity: Decimal
    price: Decimal
    reduce_only: bool
    post_only: bool
    client_order_id: str

    def to_public_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "positionSide": self.position_side.value,
            "type": self.order_type,
            "timeInForce": self.time_in_force.value,
            "quantity": decimal_str(self.quantity),
            "price": decimal_str(self.price),
            "reduceOnly": self.reduce_only,
            "postOnlyIntent": self.post_only,
            "newClientOrderId": self.client_order_id,
            "signed_request": False,
            "submitted": False,
        }


def validate_backend_caller(caller: str) -> None:
    normalized = caller.strip().lower()
    if normalized in {"browser", "frontend", "web", "client"}:
        raise ConnectorBoundaryError("browser code must never sign exchange requests")


def backend_credential_metadata(config: RuntimeConfig) -> dict[str, object]:
    return {
        "credential_scope": config.credential_scope.value,
        "api_key_present": config.binance_api_key_present,
        "api_secret_present": config.binance_api_secret_present,
        "testnet_api_key_present": config.binance_testnet_api_key_present,
        "testnet_api_secret_present": config.binance_testnet_api_secret_present,
        "live_readonly_api_key_present": (
            config.binance_live_readonly_api_key_present
        ),
        "live_readonly_api_secret_present": (
            config.binance_live_readonly_api_secret_present
        ),
        "secrets_redacted": True,
    }


def build_usdm_request_specs() -> tuple[BinanceRequestSpec, ...]:
    return (
        BinanceRequestSpec(
            "exchange_info",
            "GET",
            "/fapi/v1/exchangeInfo",
            False,
            "Binance USD-M Futures Exchange Information",
        ),
        BinanceRequestSpec(
            "user_commission_rate",
            "GET",
            "/fapi/v1/commissionRate",
            True,
            "Binance USD-M Futures User Commission Rate",
        ),
        BinanceRequestSpec(
            "account_information_v3",
            "GET",
            "/fapi/v3/account",
            True,
            "Binance USD-M Futures Account Information V3",
        ),
        BinanceRequestSpec(
            "position_mode",
            "GET",
            "/fapi/v1/positionSide/dual",
            True,
            "Binance USD-M Futures Get Current Position Mode",
        ),
        BinanceRequestSpec(
            "start_user_data_stream",
            "POST",
            "/fapi/v1/listenKey",
            False,
            "Binance USD-M Futures Start User Data Stream",
        ),
        BinanceRequestSpec(
            "new_order",
            "POST",
            "/fapi/v1/order",
            True,
            "Binance USD-M Futures New Order",
        ),
    )


def _is_multiple(value: Decimal, step: Decimal) -> bool:
    if step <= 0:
        return False
    return value % step == 0


def _metadata_errors(intent: PaperOrderIntent, metadata: SymbolMetadata) -> list[str]:
    errors: list[str] = []
    if metadata.filters is None:
        return ["symbol filters are unavailable"]
    filters = metadata.filters
    if intent.symbol != metadata.symbol:
        errors.append("intent symbol does not match metadata symbol")
    if not metadata.is_executable():
        errors.append("symbol is not executable under current symbol policy")
    if intent.time_in_force != TimeInForce.GTX:
        errors.append("post-only Binance validation requires GTX timeInForce")
    if not _is_multiple(intent.limit_price, filters.tick_size):
        errors.append("price does not align to Binance tick size")
    if not _is_multiple(intent.quantity, filters.lot_size):
        errors.append("quantity does not align to Binance lot size")
    if intent.notional < filters.min_notional:
        errors.append("notional is below Binance min notional")
    return errors


def validate_usdm_order_payload(
    intent: PaperOrderIntent,
    metadata: SymbolMetadata,
    *,
    config: RuntimeConfig,
    caller: str = "backend_api",
) -> tuple[BinanceUsdmOrderPayload | None, tuple[str, ...]]:
    """Translate a validated intent into a Binance-shaped payload without sending it."""

    reasons: list[str] = []
    try:
        validate_backend_caller(caller)
    except ConnectorBoundaryError as exc:
        reasons.append(str(exc))
    if config.venue_target not in {
        VenueTarget.BINANCE_TESTNET,
        VenueTarget.BINANCE_LIVE,
    }:
        reasons.append("Binance payload validation requires a Binance venue target")
    if config.venue_target == VenueTarget.BINANCE_LIVE:
        reasons.append("live Binance order payload validation is out of scope")
    if config.credential_scope != CredentialScope.TRADING:
        reasons.append("Binance order payload validation requires trading credentials")
    if config.venue_target == VenueTarget.BINANCE_TESTNET:
        purpose_credentials_present = (
            config.binance_testnet_credentials_present
            or config.legacy_binance_credentials_present
        )
    else:
        purpose_credentials_present = (
            config.binance_live_readonly_credentials_present
            or config.legacy_binance_credentials_present
        )
    if not purpose_credentials_present:
        reasons.append("Binance credentials must be present in the backend runtime")
    if not intent.post_only or intent.allow_taker:
        reasons.append("Binance validation remains maker-first and taker-gated")
    reasons.extend(_metadata_errors(intent, metadata))
    if reasons:
        return None, tuple(reasons)
    return (
        BinanceUsdmOrderPayload(
            symbol=intent.symbol,
            side=intent.side,
            position_side=intent.book_side,
            order_type="LIMIT",
            time_in_force=intent.time_in_force,
            quantity=intent.quantity,
            price=intent.limit_price,
            reduce_only=intent.reduce_only,
            post_only=intent.post_only,
            client_order_id=intent.client_order_id,
        ),
        (),
    )
