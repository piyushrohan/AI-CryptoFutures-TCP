"""Durable-command ledger contracts.

The in-memory implementation is used by tests and the local FastAPI surface.
Production storage is expected to persist the same public fields in Postgres.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Mapping

from services.audit.records import payload_fingerprint


class CommandLedgerError(ValueError):
    """Raised when idempotency or ledger state is invalid."""


class CommandLifecycleStatus(str, Enum):
    RECEIVED = "received"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class CommandLedgerEntry:
    command_id: str
    idempotency_key: str
    command_type: str
    actor_id: str
    payload_fingerprint: str
    status: CommandLifecycleStatus
    runtime: Mapping[str, Any]
    audit_record_id: str | None
    created_at: str
    updated_at: str
    duplicate: bool = False

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "command_id": self.command_id,
            "idempotency_key": self.idempotency_key,
            "command_type": self.command_type,
            "actor_id": self.actor_id,
            "payload_fingerprint": self.payload_fingerprint,
            "status": self.status.value,
            "runtime": dict(self.runtime),
            "audit_record_id": self.audit_record_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "duplicate": self.duplicate,
        }


class InMemoryCommandLedger:
    def __init__(self) -> None:
        self._entries: list[CommandLedgerEntry] = []
        self._by_idempotency_key: dict[str, CommandLedgerEntry] = {}

    def record_received(
        self,
        *,
        command_type: str,
        actor_id: str,
        payload: Mapping[str, Any],
        runtime: Mapping[str, Any],
        idempotency_key: str,
    ) -> CommandLedgerEntry:
        if not idempotency_key:
            raise CommandLedgerError("idempotency_key is required")
        fingerprint = payload_fingerprint(payload)
        existing = self._by_idempotency_key.get(idempotency_key)
        if existing:
            if (
                existing.command_type != command_type
                or existing.payload_fingerprint != fingerprint
            ):
                raise CommandLedgerError(
                    "idempotency_key was already used for a different command"
                )
            return replace(existing, duplicate=True)

        now = datetime.now(UTC).isoformat()
        entry = CommandLedgerEntry(
            command_id=f"cmd-{len(self._entries) + 1:06d}",
            idempotency_key=idempotency_key,
            command_type=command_type,
            actor_id=actor_id,
            payload_fingerprint=fingerprint,
            status=CommandLifecycleStatus.RECEIVED,
            runtime=runtime,
            audit_record_id=None,
            created_at=now,
            updated_at=now,
        )
        self._entries.append(entry)
        self._by_idempotency_key[idempotency_key] = entry
        return entry

    def record_decision(
        self,
        command_id: str,
        *,
        accepted: bool,
        audit_record_id: str | None,
    ) -> CommandLedgerEntry:
        status = (
            CommandLifecycleStatus.ACCEPTED
            if accepted
            else CommandLifecycleStatus.REJECTED
        )
        return self._replace(command_id, status=status, audit_record_id=audit_record_id)

    def record_completed(self, command_id: str) -> CommandLedgerEntry:
        return self._replace(command_id, status=CommandLifecycleStatus.COMPLETED)

    def records(self) -> tuple[CommandLedgerEntry, ...]:
        return tuple(self._entries)

    def to_public_list(self) -> list[dict[str, Any]]:
        return [entry.to_public_dict() for entry in self._entries]

    def _replace(
        self,
        command_id: str,
        *,
        status: CommandLifecycleStatus,
        audit_record_id: str | None = None,
    ) -> CommandLedgerEntry:
        for index, entry in enumerate(self._entries):
            if entry.command_id != command_id:
                continue
            updated = replace(
                entry,
                status=status,
                audit_record_id=(
                    audit_record_id
                    if audit_record_id is not None
                    else entry.audit_record_id
                ),
                updated_at=datetime.now(UTC).isoformat(),
            )
            self._entries[index] = updated
            self._by_idempotency_key[updated.idempotency_key] = updated
            return updated
        raise CommandLedgerError(f"unknown command_id: {command_id}")
