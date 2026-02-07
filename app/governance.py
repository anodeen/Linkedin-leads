from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class AuditEvent:
    event_id: int
    action: str
    payload: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLog:
    """Append-only audit log for compliance and operational traceability."""

    def __init__(self) -> None:
        self._next_event_id = 1
        self._events: list[AuditEvent] = []

    def append(self, action: str, payload: dict[str, Any]) -> AuditEvent:
        event = AuditEvent(event_id=self._next_event_id, action=action, payload=dict(payload))
        self._next_event_id += 1
        self._events.append(event)
        return event

    def list_events(self) -> list[AuditEvent]:
        return list(self._events)


    def purge_older_than(self, cutoff) -> int:
        before = len(self._events)
        self._events = [event for event in self._events if event.created_at >= cutoff]
        return before - len(self._events)
