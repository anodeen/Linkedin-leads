from dataclasses import dataclass

from .approval import ApprovalStatus, DraftApproval
from .delivery import DeliveryEvent, DeliveryEventType
from .models import Lead


@dataclass(slots=True)
class ActivityMetrics:
    leads_ingested: int
    drafts_submitted: int
    drafts_reviewed: int
    approved_drafts: int
    rejected_drafts: int


@dataclass(slots=True)
class FunnelMetrics:
    leads_total: int
    leads_with_approved_draft: int
    messages_sent: int
    messages_delivered: int
    messages_bounced: int
    complaints: int


@dataclass(slots=True)
class ManagerDashboardSnapshot:
    activity: ActivityMetrics
    funnel: FunnelMetrics


class ManagerDashboardBuilder:
    """PRD Step 6: manager-facing activity and conversion funnel summary."""

    def build(
        self,
        leads: list[Lead],
        approvals: list[DraftApproval],
        delivery_events: list[DeliveryEvent],
    ) -> ManagerDashboardSnapshot:
        drafts_reviewed = sum(1 for item in approvals if item.status != ApprovalStatus.PENDING)
        approved_drafts = sum(1 for item in approvals if item.status == ApprovalStatus.APPROVED)
        rejected_drafts = sum(1 for item in approvals if item.status == ApprovalStatus.REJECTED)

        approved_leads = {item.lead_id for item in approvals if item.status == ApprovalStatus.APPROVED}

        sent = sum(1 for event in delivery_events if event.event_type == DeliveryEventType.SENT)
        delivered = sum(1 for event in delivery_events if event.event_type == DeliveryEventType.DELIVERED)
        bounced = sum(1 for event in delivery_events if event.event_type == DeliveryEventType.BOUNCED)
        complaints = sum(1 for event in delivery_events if event.event_type == DeliveryEventType.COMPLAINT)

        activity = ActivityMetrics(
            leads_ingested=len(leads),
            drafts_submitted=len(approvals),
            drafts_reviewed=drafts_reviewed,
            approved_drafts=approved_drafts,
            rejected_drafts=rejected_drafts,
        )
        funnel = FunnelMetrics(
            leads_total=len(leads),
            leads_with_approved_draft=len(approved_leads),
            messages_sent=sent,
            messages_delivered=delivered,
            messages_bounced=bounced,
            complaints=complaints,
        )
        return ManagerDashboardSnapshot(activity=activity, funnel=funnel)
