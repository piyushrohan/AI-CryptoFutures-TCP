"""Order reconciliation contracts for external venue lanes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Mapping


class VenueOrderStatus(str, Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


_STATUS_RANK = {
    VenueOrderStatus.NEW: 10,
    VenueOrderStatus.PARTIALLY_FILLED: 20,
    VenueOrderStatus.FILLED: 90,
    VenueOrderStatus.CANCELED: 90,
    VenueOrderStatus.EXPIRED: 90,
    VenueOrderStatus.REJECTED: 90,
}


@dataclass(frozen=True)
class VenueOrderUpdate:
    venue_target: str
    order_id: str
    client_order_id: str
    status: VenueOrderStatus
    execution_type: str
    payload: Mapping[str, Any]
    event_time: datetime

    @classmethod
    def from_binance_order_trade_update(
        cls,
        payload: Mapping[str, Any],
        *,
        venue_target: str,
    ) -> "VenueOrderUpdate":
        event = payload.get("o", {})
        if not isinstance(event, Mapping):
            raise ValueError("ORDER_TRADE_UPDATE payload must include order object")
        event_time_ms = int(payload.get("E", 0))
        event_time = (
            datetime.fromtimestamp(event_time_ms / 1000, tz=UTC)
            if event_time_ms
            else datetime.now(UTC)
        )
        return cls(
            venue_target=venue_target,
            order_id=str(event.get("i", "")),
            client_order_id=str(event.get("c", "")),
            status=VenueOrderStatus(str(event.get("X", VenueOrderStatus.NEW.value))),
            execution_type=str(event.get("x", "")),
            payload=dict(payload),
            event_time=event_time,
        )

    def to_public_dict(self) -> dict[str, object]:
        return {
            "venue_target": self.venue_target,
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "status": self.status.value,
            "execution_type": self.execution_type,
            "event_time": self.event_time.isoformat(),
        }


@dataclass(frozen=True)
class ReconciliationDecision:
    accepted: bool
    reason: str
    previous_status: str | None
    update: VenueOrderUpdate

    def to_public_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "reason": self.reason,
            "previous_status": self.previous_status,
            "update": self.update.to_public_dict(),
        }


class MonotonicOrderReconciler:
    """Reject duplicate or regressive venue order updates."""

    def __init__(self) -> None:
        self._status_by_order_id: dict[str, VenueOrderStatus] = {}

    def apply(self, update: VenueOrderUpdate) -> ReconciliationDecision:
        previous = self._status_by_order_id.get(update.order_id)
        if previous == update.status:
            return ReconciliationDecision(
                accepted=False,
                reason="duplicate order status update",
                previous_status=previous.value,
                update=update,
            )
        if previous and _STATUS_RANK[update.status] < _STATUS_RANK[previous]:
            return ReconciliationDecision(
                accepted=False,
                reason="regressive order status update",
                previous_status=previous.value,
                update=update,
            )
        self._status_by_order_id[update.order_id] = update.status
        return ReconciliationDecision(
            accepted=True,
            reason="order status update accepted",
            previous_status=previous.value if previous else None,
            update=update,
        )
