"""Audit record scaffolding.

Phase 1 keeps audit records in memory for local validation only. The important
behavior is the contract: every command decision gets a record, and records do
not store secret-bearing payload values.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping

from services.storage import JsonStateStore


_SENSITIVE_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "credential",
    "jwt",
    "password",
    "private",
    "secret",
    "token",
)


def _is_sensitive_key(key: object) -> bool:
    normalized = str(key).lower()
    return any(fragment in normalized for fragment in _SENSITIVE_KEY_FRAGMENTS)


def _shape_only(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "<redacted>" if _is_sensitive_key(key) else _shape_only(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, list | tuple):
        return [_shape_only(item) for item in value]
    if value is None:
        return None
    return f"<{type(value).__name__}>"


def payload_fingerprint(payload: Mapping[str, Any]) -> str:
    shape = _shape_only(payload)
    body = json.dumps(shape, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class AuditRecord:
    record_id: str
    command_type: str
    actor_id: str
    decision: str
    reasons: tuple[str, ...]
    payload_keys: tuple[str, ...]
    payload_fingerprint: str
    runtime: Mapping[str, Any]
    created_at: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "command_type": self.command_type,
            "actor_id": self.actor_id,
            "decision": self.decision,
            "reasons": list(self.reasons),
            "payload_keys": list(self.payload_keys),
            "payload_fingerprint": self.payload_fingerprint,
            "runtime": dict(self.runtime),
            "created_at": self.created_at,
        }


class InMemoryAuditRecorder:
    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def record_decision(
        self,
        *,
        command_type: str,
        actor_id: str,
        decision: str,
        reasons: list[str],
        payload: Mapping[str, Any],
        runtime: Mapping[str, Any],
    ) -> AuditRecord:
        record_number = len(self._records) + 1
        fingerprint = payload_fingerprint(payload)
        record = AuditRecord(
            record_id=f"audit-{record_number:06d}",
            command_type=command_type,
            actor_id=actor_id,
            decision=decision,
            reasons=tuple(reasons),
            payload_keys=tuple(sorted(str(key) for key in payload.keys())),
            payload_fingerprint=fingerprint,
            runtime=runtime,
            created_at=datetime.now(UTC).isoformat(),
        )
        self._records.append(record)
        return record

    def records(self) -> tuple[AuditRecord, ...]:
        return tuple(self._records)

    def to_public_list(self) -> list[dict[str, Any]]:
        return [record.to_public_dict() for record in self._records]


class FileBackedAuditRecorder(InMemoryAuditRecorder):
    def __init__(
        self,
        store: JsonStateStore | None = None,
        *,
        jsonl_name: str = "audit/records.jsonl",
    ) -> None:
        super().__init__()
        self._store = store or JsonStateStore()
        self._jsonl_name = jsonl_name
        for row in self._store.read_jsonl(self._jsonl_name):
            self._records.append(
                AuditRecord(
                    record_id=str(row["record_id"]),
                    command_type=str(row["command_type"]),
                    actor_id=str(row["actor_id"]),
                    decision=str(row["decision"]),
                    reasons=tuple(str(item) for item in row.get("reasons", [])),
                    payload_keys=tuple(
                        str(item) for item in row.get("payload_keys", [])
                    ),
                    payload_fingerprint=str(row["payload_fingerprint"]),
                    runtime=dict(row.get("runtime", {})),
                    created_at=str(row["created_at"]),
                )
            )

    def record_decision(
        self,
        *,
        command_type: str,
        actor_id: str,
        decision: str,
        reasons: list[str],
        payload: Mapping[str, Any],
        runtime: Mapping[str, Any],
    ) -> AuditRecord:
        record = super().record_decision(
            command_type=command_type,
            actor_id=actor_id,
            decision=decision,
            reasons=reasons,
            payload=payload,
            runtime=runtime,
        )
        self._store.append_jsonl(self._jsonl_name, record.to_public_dict())
        self._store.write_json(
            "audit/latest.json",
            {"records": self.to_public_list()},
        )
        return record
