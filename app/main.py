from .models import DataSource, InboundLead, IngestLeadsResponse, Lead
from .store import LeadStore


class LeadIngestionService:
    """Step 1 service: compliance-first ingestion from official/vetted sources only."""

    def __init__(self, store: LeadStore | None = None) -> None:
        self.store = store or LeadStore()

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
