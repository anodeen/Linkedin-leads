from .models import DataSource, InboundLead, IngestLeadsResponse, Lead
from .scoring import ICPRuleConfig, LeadScoreResult, RuleBasedScorer
from .store import LeadStore


class LeadIngestionService:
    """PRD Step 1 + Step 2: ingestion and ICP-configurable rule-based scoring."""

    def __init__(self, store: LeadStore | None = None, scorer: RuleBasedScorer | None = None) -> None:
        self.store = store or LeadStore()
        self.scorer = scorer or RuleBasedScorer()

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
