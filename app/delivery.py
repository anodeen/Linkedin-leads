from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class OutboundChannel(str, Enum):
    EMAIL = "email"


class DeliveryEventType(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    COMPLAINT = "complaint"


@dataclass(slots=True)
class DeliveryEvent:
    event_id: int
    lead_id: int
    channel: OutboundChannel
    recipient: str
    subject: str
    event_type: DeliveryEventType
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DeliveryTelemetry:
    """PRD Step 5: outbound send + delivery telemetry events."""

    def __init__(self) -> None:
        self._next_event_id = 1
        self._events: list[DeliveryEvent] = []

    def send_email(self, lead_id: int, recipient: str, subject: str) -> DeliveryEvent:
        if "@" not in recipient or "." not in recipient.split("@")[-1]:
            raise ValueError("recipient must be a valid email")
        return self.record_event(
            lead_id=lead_id,
            channel=OutboundChannel.EMAIL,
            recipient=recipient,
            subject=subject,
            event_type=DeliveryEventType.SENT,
        )

    def record_event(
        self,
        lead_id: int,
        channel: OutboundChannel,
        recipient: str,
        subject: str,
        event_type: DeliveryEventType,
    ) -> DeliveryEvent:
        event = DeliveryEvent(
            event_id=self._next_event_id,
            lead_id=lead_id,
            channel=channel,
            recipient=recipient,
            subject=subject,
            event_type=event_type,
        )
        self._next_event_id += 1
        self._events.append(event)
        return event

    def list_events(self, lead_id: int | None = None) -> list[DeliveryEvent]:
        if lead_id is None:
            return list(self._events)
        return [event for event in self._events if event.lead_id == lead_id]

    def purge_lead(self, lead_id: int) -> int:
        before = len(self._events)
        self._events = [event for event in self._events if event.lead_id != lead_id]
        return before - len(self._events)


    def purge_older_than(self, cutoff) -> int:
        before = len(self._events)
        self._events = [event for event in self._events if event.created_at >= cutoff]
        return before - len(self._events)
