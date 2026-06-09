"""LIVE read-only account visibility scaffolding."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from libs.binance_connector import backend_credential_metadata
from libs.config import RuntimeConfig
from libs.schemas import CommandRequest, CommandType, default_account_state
from services.audit import InMemoryAuditRecorder
from services.risk import evaluate_command


@dataclass(frozen=True)
class LiveReadonlySnapshot:
    account_state: dict[str, Any]
    commission_state: dict[str, object]
    mode_state: dict[str, object]
    reconciliation: dict[str, object]
    inspected_at: datetime

    def to_public_dict(self) -> dict[str, object]:
        return {
            "account_state": self.account_state,
            "commission_state": self.commission_state,
            "mode_state": self.mode_state,
            "reconciliation": self.reconciliation,
            "inspected_at": self.inspected_at.isoformat(),
        }


def _snapshot() -> LiveReadonlySnapshot:
    now = datetime.now(UTC)
    account = default_account_state(now).to_public_dict(now)
    return LiveReadonlySnapshot(
        account_state=account,
        commission_state={
            "source": "backend_readonly_projection",
            "maker_fee_rate": "requires_live_readonly_fetch",
            "taker_fee_rate": "requires_live_readonly_fetch",
            "network_calls": "not_performed_in_ci",
        },
        mode_state={
            "position_mode": account["position_mode"],
            "margin_mode": account["margin_mode"],
            "hedge_mode_books": "independent_LONG_SHORT_books",
        },
        reconciliation={
            "status": "audit_only",
            "local_state_compared": True,
            "differences": [],
            "order_submission": "forbidden",
        },
        inspected_at=now,
    )


def live_readonly_account_payload(
    config: RuntimeConfig | None = None,
    *,
    recorder: InMemoryAuditRecorder | None = None,
) -> dict[str, object]:
    runtime = config or RuntimeConfig()
    result = evaluate_command(
        runtime,
        CommandRequest(CommandType.GET_LIVE_READONLY_ACCOUNT),
        fee_model_available=True,
    )
    reasons = list(result.reasons)
    readonly_credentials_present = (
        runtime.binance_live_readonly_credentials_present
        or runtime.legacy_binance_credentials_present
    )
    if not readonly_credentials_present:
        reasons.append("read-only Binance credentials must be present in backend")
    accepted = result.accepted and not reasons
    audit_record = None
    if recorder:
        audit_record = recorder.record_decision(
            command_type=CommandType.GET_LIVE_READONLY_ACCOUNT.value,
            actor_id="local_operator",
            decision="accepted" if accepted else "rejected",
            reasons=reasons,
            payload={"scope": "live_readonly"},
            runtime=runtime.to_status(),
        ).to_public_dict()
    return {
        "status": "ok",
        "service": "live_readonly",
        "accepted": accepted,
        "reasons": reasons,
        "runtime": runtime.to_status(),
        "credential_metadata": backend_credential_metadata(runtime),
        "snapshot": _snapshot().to_public_dict() if accepted else None,
        "audit_record": audit_record,
        "order_submission": "forbidden",
    }


def live_order_rejection_payload(config: RuntimeConfig | None = None) -> dict[str, object]:
    runtime = config or RuntimeConfig()
    return {
        "status": "ok",
        "service": "live_readonly",
        "accepted": False,
        "order_submission": "forbidden",
        "reasons": [
            "Phase 10 live-trade order submission is out of scope",
            "live trading remains fail-closed",
            "browser signing is forbidden",
        ],
        "runtime": runtime.to_status(),
    }
