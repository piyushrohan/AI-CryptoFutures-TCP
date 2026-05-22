"""File-backed persistence for public paper-exchange state."""

from __future__ import annotations

from typing import Any, Mapping

from services.storage import JsonStateStore


class PaperExchangeStateStore:
    def __init__(self, store: JsonStateStore | None = None) -> None:
        self._store = store or JsonStateStore()

    def persist_snapshot(self, payload: Mapping[str, Any]) -> None:
        self._store.write_json("paper/latest.json", payload)
        self._store.append_jsonl(
            "paper/snapshots.jsonl",
            {
                "status": payload.get("status"),
                "service": payload.get("service"),
                "orders_count": payload.get("orders_count"),
                "reconciliation_count": payload.get("reconciliation_count"),
                "portfolio": payload.get("portfolio"),
                "panic_halted": payload.get("panic_halted"),
            },
        )

    def persist_orders(self, payload: Mapping[str, Any]) -> None:
        self._store.write_json("paper/orders.json", payload)

    def persist_reconciliation(self, payload: Mapping[str, Any]) -> None:
        self._store.write_json("paper/reconciliation.json", payload)

    def persist_portfolio(self, payload: Mapping[str, Any]) -> None:
        self._store.write_json("paper/portfolio.json", payload)

    def latest_snapshot(self) -> dict[str, Any]:
        return self._store.read_json("paper/latest.json")
