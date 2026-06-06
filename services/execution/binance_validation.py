"""Binance USDⓈ-M Futures validation lanes.

These helpers are deliberately validation-only. They let the API prove that
runtime gates, symbol filters, hedge-mode fields, and maker-first intent are
understood before any real connector work is allowed.
"""

from __future__ import annotations

from typing import Any, Mapping

from libs.binance_connector import (
    backend_credential_metadata,
    build_usdm_request_specs,
    validate_usdm_order_payload,
)
from libs.config import AutonomyStage, CredentialScope, RuntimeConfig, VenueTarget
from libs.schemas import (
    CommandRequest,
    CommandType,
    PaperOrderIntent,
    default_account_state,
)
from services.risk import evaluate_command


def _metadata_for(symbol: str):
    account = default_account_state()
    for item in account.symbol_metadata:
        if item.symbol == symbol:
            return item
    return None


def testnet_validation_payload(
    config: RuntimeConfig | None = None,
) -> dict[str, object]:
    runtime = config or RuntimeConfig()
    result = evaluate_command(
        runtime,
        CommandRequest(CommandType.CREATE_TESTNET_VALIDATION_SESSION),
        fee_model_available=True,
    )
    return {
        "status": "ok",
        "service": "binance_validation",
        "lane": "binance_testnet",
        "accepted": result.accepted,
        "reasons": list(result.reasons),
        "runtime": runtime.to_status(),
        "credential_metadata": backend_credential_metadata(runtime),
        "request_specs": [
            item.to_public_dict() for item in build_usdm_request_specs()
        ],
        "network_calls": "not_performed",
        "order_submission": "not_performed",
    }


def testnet_order_validation_payload(
    body: Mapping[str, Any] | None = None,
    *,
    config: RuntimeConfig | None = None,
) -> dict[str, object]:
    runtime = config or RuntimeConfig()
    payload = dict(body or {})
    intent = PaperOrderIntent.from_mapping(payload)
    result = evaluate_command(
        runtime,
        CommandRequest(CommandType.SUBMIT_TESTNET_ORDER, payload=payload),
        fee_model_available=True,
    )
    metadata = _metadata_for(intent.symbol)
    translated = None
    translation_reasons: tuple[str, ...]
    if metadata is None:
        translation_reasons = (f"{intent.symbol} metadata is unavailable",)
    else:
        translated, translation_reasons = validate_usdm_order_payload(
            intent,
            metadata,
            config=runtime,
            caller="backend_api",
        )
    accepted = result.accepted and translated is not None and not translation_reasons
    return {
        "status": "ok",
        "service": "binance_validation",
        "lane": "binance_testnet",
        "accepted": accepted,
        "command": result.to_public_dict(),
        "translation_reasons": list(translation_reasons),
        "binance_payload": translated.to_public_dict() if translated else None,
        "network_calls": "not_performed",
        "order_submission": "not_performed",
        "notes": [
            "backend-only validation lane",
            "Binance testnet is not a top-level operator mode",
            "no request signing or submission occurs",
        ],
    }


def testnet_runtime_fixture() -> RuntimeConfig:
    return RuntimeConfig(
        venue_target=VenueTarget.BINANCE_TESTNET,
        credential_scope=CredentialScope.TRADING,
        autonomy_stage=AutonomyStage.TESTNET_AUTO,
        binance_api_key_present=True,
        binance_api_secret_present=True,
    )
