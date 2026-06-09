"""Postgres production-storage configuration and migration manifest."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


PRODUCTION_TABLES: tuple[str, ...] = (
    "audit_records",
    "command_ledger",
    "account_snapshots",
    "symbol_metadata_snapshots",
    "fee_policy_snapshots",
    "paper_orders",
    "paper_fills",
    "reconciliation_events",
    "model_registry_entries",
    "strategy_sessions",
    "runtime_config_versions",
)


@dataclass(frozen=True)
class PostgresSettings:
    database_url: str | None
    migrations_enabled: bool = True

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "PostgresSettings":
        values = os.environ if env is None else env
        return cls(
            database_url=values.get("DATABASE_URL"),
            migrations_enabled=values.get("TCP_MIGRATIONS_ENABLED", "true").lower()
            not in {"0", "false", "no", "off"},
        )

    @property
    def configured(self) -> bool:
        return bool(self.database_url)

    def to_public_dict(self) -> dict[str, object]:
        return {
            "configured": self.configured,
            "migrations_enabled": self.migrations_enabled,
            "database_url_present": bool(self.database_url),
            "database_url_redacted": True,
            "required_tables": list(PRODUCTION_TABLES),
        }
