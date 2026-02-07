from .approval import ApprovalWorkflow, DraftApproval
from .delivery import DeliveryEvent, DeliveryEventType, DeliveryTelemetry, OutboundChannel
from .messaging import MessageDraft, MessageDraftGenerator, MessageGenerationControls
from .models import DataSource, InboundLead, IngestLeadsResponse, Lead
from .scoring import ICPRuleConfig, LeadScoreResult, RuleBasedScorer
from .store import LeadStore


class LeadIngestionService:
    """PRD Step 1-5: ingestion, scoring, draft generation, approval, and delivery telemetry."""

    def __init__(
        self,
        store: LeadStore | None = None,
        scorer: RuleBasedScorer | None = None,
        drafter: MessageDraftGenerator | None = None,
        approvals: ApprovalWorkflow | None = None,
        delivery: DeliveryTelemetry | None = None,
    ) -> None:
        self.store = store or LeadStore()
        self.scorer = scorer or RuleBasedScorer()
        self.drafter = drafter or MessageDraftGenerator()
        self.approvals = approvals or ApprovalWorkflow()
        self.delivery = delivery or DeliveryTelemetry()

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
        return IngestLeadsResponse(
            provider_name=provider_name,
            accepted=len(created),
            rejected=0,
            lead_ids=[lead.id for lead in created],
        )

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
        return self.approvals.submit(lead_id=lead_id, draft=draft)

    def review_draft(
        self,
        revision_id: int,
        reviewer: str,
        approve: bool,
        review_notes: str | None = None,
    ) -> DraftApproval:
        if len(reviewer.strip()) < 2:
            raise ValueError("reviewer must be at least 2 characters")
        return self.approvals.review(
            revision_id=revision_id,
            reviewer=reviewer,
            approve=approve,
            review_notes=review_notes,
        )

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
        return self.delivery.send_email(
            lead_id=lead_id,
            recipient=recipient_email,
            subject=approved.draft.subject,
        )

    def record_delivery_event(
        self,
        lead_id: int,
        event_type: DeliveryEventType,
        recipient_email: str,
    ) -> DeliveryEvent:
        approved = self.approvals.get_latest_approved(lead_id)
        if approved is None:
            raise ValueError(f"lead_id {lead_id} cannot record delivery event without approved draft")
        return self.delivery.record_event(
            lead_id=lead_id,
            channel=OutboundChannel.EMAIL,
            recipient=recipient_email,
            subject=approved.draft.subject,
            event_type=event_type,
        )

    def list_delivery_events(self, lead_id: int | None = None) -> list[DeliveryEvent]:
        return self.delivery.list_events(lead_id=lead_id)
