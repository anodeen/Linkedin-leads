from .approval import ApprovalWorkflow, DraftApproval
from .crm import CRMOutcomeRecord, CRMOutcomeSync, OutcomeStatus, ScoringQualitySnapshot
from .delivery import DeliveryEvent, DeliveryEventType, DeliveryTelemetry, OutboundChannel
from .governance import AuditEvent, AuditLog
from .messaging import MessageDraft, MessageDraftGenerator, MessageGenerationControls
from .models import DataSource, InboundLead, IngestLeadsResponse, Lead
from .reporting import ManagerDashboardBuilder, ManagerDashboardSnapshot
from .scoring import ICPRuleConfig, LeadScoreResult, RuleBasedScorer
from .store import LeadStore


class LeadIngestionService:
    """PRD Step 1-7 + hardening: includes audit logging for traceability."""

    def __init__(
        self,
        store: LeadStore | None = None,
        scorer: RuleBasedScorer | None = None,
        drafter: MessageDraftGenerator | None = None,
        approvals: ApprovalWorkflow | None = None,
        delivery: DeliveryTelemetry | None = None,
        dashboard: ManagerDashboardBuilder | None = None,
        crm_sync: CRMOutcomeSync | None = None,
        audit: AuditLog | None = None,
    ) -> None:
        self.store = store or LeadStore()
        self.scorer = scorer or RuleBasedScorer()
        self.drafter = drafter or MessageDraftGenerator()
        self.approvals = approvals or ApprovalWorkflow()
        self.delivery = delivery or DeliveryTelemetry()
        self.dashboard = dashboard or ManagerDashboardBuilder()
        self.crm_sync = crm_sync or CRMOutcomeSync()
        self.audit = audit or AuditLog()

    def configure_icp(self, config: ICPRuleConfig) -> None:
        self.scorer = RuleBasedScorer(config=config)

    def ingest(self, provider_name: str, leads: list[InboundLead]) -> IngestLeadsResponse:
        if len(provider_name.strip()) < 2:
            raise ValueError("provider_name must be at least 2 characters")
        if not leads:
            raise ValueError("at least one lead is required")

        for lead in leads:
            lead.validate()
            if lead.source not in {DataSource.OFFICIAL_API, DataSource.VETTED_PROVIDER}:
                raise ValueError(f"Unsupported source: {lead.source}")

        created = self.store.add_many(leads)
        response = IngestLeadsResponse(
            provider_name=provider_name,
            accepted=len(created),
            rejected=0,
            lead_ids=[lead.id for lead in created],
        )
        self.audit.append(
            action="lead_batch_ingested",
            payload={"provider_name": provider_name, "accepted": response.accepted, "lead_ids": response.lead_ids},
        )
        return response

    def list_leads(self) -> list[Lead]:
        return self.store.list_all()

    def score_lead(self, lead_id: int) -> LeadScoreResult:
        lead = self.store.get_by_id(lead_id)
        if lead is None:
            raise ValueError(f"lead_id {lead_id} not found")

        inbound = InboundLead(
            full_name=lead.full_name,
            title=lead.title,
            company=lead.company,
            profile_url=lead.profile_url,
            source=lead.source,
        )
        return self.scorer.score_lead(inbound)

    def generate_message_draft(self, lead_id: int, controls: MessageGenerationControls) -> MessageDraft:
        lead = self.store.get_by_id(lead_id)
        if lead is None:
            raise ValueError(f"lead_id {lead_id} not found")
        return self.drafter.generate(lead=lead, controls=controls)

    def submit_draft_for_approval(self, lead_id: int, draft: MessageDraft) -> DraftApproval:
        if self.store.get_by_id(lead_id) is None:
            raise ValueError(f"lead_id {lead_id} not found")
        approval = self.approvals.submit(lead_id=lead_id, draft=draft)
        self.audit.append(
            action="draft_submitted_for_approval",
            payload={"lead_id": lead_id, "revision_id": approval.revision_id},
        )
        return approval

    def review_draft(
        self,
        revision_id: int,
        reviewer: str,
        approve: bool,
        review_notes: str | None = None,
    ) -> DraftApproval:
        if len(reviewer.strip()) < 2:
            raise ValueError("reviewer must be at least 2 characters")
        reviewed = self.approvals.review(
            revision_id=revision_id,
            reviewer=reviewer,
            approve=approve,
            review_notes=review_notes,
        )
        self.audit.append(
            action="draft_reviewed",
            payload={
                "revision_id": revision_id,
                "lead_id": reviewed.lead_id,
                "status": reviewed.status.value,
                "reviewer": reviewed.reviewer,
            },
        )
        return reviewed

    def assert_send_allowed(self, lead_id: int) -> None:
        if self.store.get_by_id(lead_id) is None:
            raise ValueError(f"lead_id {lead_id} not found")
        if not self.approvals.is_send_allowed(lead_id):
            raise ValueError(
                f"lead_id {lead_id} cannot be sent: at least one approved revision is required"
            )

    def send_approved_message(self, lead_id: int, recipient_email: str) -> DeliveryEvent:
        self.assert_send_allowed(lead_id)
        approved = self.approvals.get_latest_approved(lead_id)
        if approved is None:
            raise ValueError(f"lead_id {lead_id} cannot be sent: no approved draft found")
        event = self.delivery.send_email(
            lead_id=lead_id,
            recipient=recipient_email,
            subject=approved.draft.subject,
        )
        self.audit.append(
            action="message_sent",
            payload={"lead_id": lead_id, "recipient": recipient_email, "event_id": event.event_id},
        )
        return event

    def record_delivery_event(
        self,
        lead_id: int,
        event_type: DeliveryEventType,
        recipient_email: str,
    ) -> DeliveryEvent:
        approved = self.approvals.get_latest_approved(lead_id)
        if approved is None:
            raise ValueError(f"lead_id {lead_id} cannot record delivery event without approved draft")
        event = self.delivery.record_event(
            lead_id=lead_id,
            channel=OutboundChannel.EMAIL,
            recipient=recipient_email,
            subject=approved.draft.subject,
            event_type=event_type,
        )
        self.audit.append(
            action="delivery_event_recorded",
            payload={"lead_id": lead_id, "event_type": event_type.value, "event_id": event.event_id},
        )
        return event

    def list_delivery_events(self, lead_id: int | None = None) -> list[DeliveryEvent]:
        return self.delivery.list_events(lead_id=lead_id)

    def get_manager_dashboard(self) -> ManagerDashboardSnapshot:
        return self.dashboard.build(
            leads=self.store.list_all(),
            approvals=self.approvals.list_all(),
            delivery_events=self.delivery.list_events(),
        )

    def sync_crm_outcome(
        self,
        lead_id: int,
        status: OutcomeStatus,
        deal_value: float | None = None,
    ) -> CRMOutcomeRecord:
        if self.store.get_by_id(lead_id) is None:
            raise ValueError(f"lead_id {lead_id} not found")
        record = self.crm_sync.sync_outcome(lead_id=lead_id, status=status, deal_value=deal_value)
        self.audit.append(
            action="crm_outcome_synced",
            payload={"lead_id": lead_id, "status": status.value, "record_id": record.record_id},
        )
        return record

    def list_crm_outcomes(self, lead_id: int | None = None) -> list[CRMOutcomeRecord]:
        return self.crm_sync.list_outcomes(lead_id=lead_id)

    def get_scoring_quality_snapshot(self, high_score_threshold: int = 70) -> ScoringQualitySnapshot:
        outcomes = [
            item
            for item in self.crm_sync.list_outcomes()
            if item.status in {OutcomeStatus.WON, OutcomeStatus.LOST}
        ]
        if not outcomes:
            return ScoringQualitySnapshot(
                total_labeled=0,
                won_count=0,
                high_score_count=0,
                high_score_win_rate=0.0,
            )

        high_score_records = []
        won_count = 0
        for item in outcomes:
            if item.status == OutcomeStatus.WON:
                won_count += 1
            score = self.score_lead(item.lead_id).score
            if score >= high_score_threshold:
                high_score_records.append(item)

        if not high_score_records:
            high_score_win_rate = 0.0
        else:
            high_score_wins = sum(1 for item in high_score_records if item.status == OutcomeStatus.WON)
            high_score_win_rate = high_score_wins / len(high_score_records)

        return ScoringQualitySnapshot(
            total_labeled=len(outcomes),
            won_count=won_count,
            high_score_count=len(high_score_records),
            high_score_win_rate=high_score_win_rate,
        )

    def list_audit_events(self) -> list[AuditEvent]:
        return self.audit.list_events()
