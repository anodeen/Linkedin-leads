from dataclasses import dataclass

from .approval import DraftApproval
from .crm import CRMOutcomeRecord
from .delivery import DeliveryEvent
from .governance import AuditEvent
from .models import Lead


@dataclass(slots=True)
class ComplianceSnapshot:
    total_leads: int
    total_audit_events: int
    dsar_deletions_recorded: int
    retention_runs_recorded: int
    pending_approvals: int
    delivery_events_total: int
    crm_outcomes_total: int


class ComplianceReporter:
    """Step 11: compliance posture snapshot for operational readiness checks."""

    def build(
        self,
        leads: list[Lead],
        approvals: list[DraftApproval],
        delivery_events: list[DeliveryEvent],
        crm_outcomes: list[CRMOutcomeRecord],
        audit_events: list[AuditEvent],
    ) -> ComplianceSnapshot:
        dsar_deletions_recorded = sum(1 for event in audit_events if event.action == "lead_deleted")
        retention_runs_recorded = sum(
            1 for event in audit_events if event.action == "retention_policy_enforced"
        )
        pending_approvals = sum(1 for approval in approvals if approval.status.value == "pending")

        return ComplianceSnapshot(
            total_leads=len(leads),
            total_audit_events=len(audit_events),
            dsar_deletions_recorded=dsar_deletions_recorded,
            retention_runs_recorded=retention_runs_recorded,
            pending_approvals=pending_approvals,
            delivery_events_total=len(delivery_events),
            crm_outcomes_total=len(crm_outcomes),
        )
