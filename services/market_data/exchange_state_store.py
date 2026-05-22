"""Local exchange-state snapshot storage for Phase 2.

The store is intentionally in-memory and seeded from deterministic local
schemas. It is enough to exercise account, symbol, fee, and freshness contracts
without introducing Binance connectivity.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from libs.schemas import AccountState, default_account_state


class InMemoryExchangeStateStore:
    def __init__(self, seed: AccountState | None = None) -> None:
        self._snapshots: list[AccountState] = [seed or default_account_state()]

    def append(self, snapshot: AccountState) -> None:
        self._snapshots.append(snapshot)

    def latest(self) -> AccountState:
        return self._snapshots[-1]

    def snapshots(self) -> tuple[AccountState, ...]:
        return tuple(self._snapshots)


def _reference_time(reference_time: datetime | None = None) -> datetime:
    return reference_time or datetime.now(UTC)


def _fresh_snapshot(reference_time: datetime | None = None) -> AccountState:
    return default_account_state(_reference_time(reference_time))


def exchange_state_payload(reference_time: datetime | None = None) -> dict[str, Any]:
    now = _reference_time(reference_time)
    snapshot = _fresh_snapshot(now)
    return {
        "status": "ok",
        "service": "exchange_state",
        "phase": "deterministic_exchange_and_account_state",
        "account_state": snapshot.to_public_dict(now),
        "symbol_metadata": [
            item.to_public_dict(now) for item in snapshot.symbol_metadata
        ],
        "fee_policies": [
            item.to_public_dict(now) for item in snapshot.fee_policies
        ],
        "notes": [
            "local mock snapshot only",
            "no Binance connectivity",
            "no order submission",
            "Portfolio Margin is research-only",
        ],
    }


def account_state_payload(reference_time: datetime | None = None) -> dict[str, Any]:
    now = _reference_time(reference_time)
    snapshot = _fresh_snapshot(now)
    return {
        "status": "ok",
        "service": "account_state",
        "account_state": snapshot.to_public_dict(now),
    }


def symbol_metadata_payload(reference_time: datetime | None = None) -> dict[str, Any]:
    now = _reference_time(reference_time)
    snapshot = _fresh_snapshot(now)
    return {
        "status": "ok",
        "service": "symbol_metadata",
        "symbols": [item.to_public_dict(now) for item in snapshot.symbol_metadata],
    }


def fee_policy_payload(reference_time: datetime | None = None) -> dict[str, Any]:
    now = _reference_time(reference_time)
    snapshot = _fresh_snapshot(now)
    return {
        "status": "ok",
        "service": "fee_policy",
        "fee_policies": [
            item.to_public_dict(now) for item in snapshot.fee_policies
        ],
    }
