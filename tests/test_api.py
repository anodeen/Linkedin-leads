import pytest

from app.main import LeadIngestionService
from app.models import DataSource, InboundLead


def test_ingest_and_list_leads() -> None:
    service = LeadIngestionService()

    response = service.ingest(
        provider_name="proxycurl",
        leads=[
            InboundLead(
                full_name="Jane Doe",
                title="Head of Sales",
                company="Acme Inc",
                profile_url="https://www.linkedin.com/in/jane-doe",
                source=DataSource.OFFICIAL_API,
            ),
            InboundLead(
                full_name="John Smith",
                title="Revenue Operations Manager",
                company="Beta Labs",
                profile_url="https://www.linkedin.com/in/john-smith",
                source=DataSource.VETTED_PROVIDER,
            ),
        ],
    )

    assert response.accepted == 2
    assert response.rejected == 0

    leads = service.list_leads()
    assert len(leads) == 2
    assert leads[0].full_name == "Jane Doe"
    assert leads[1].source == DataSource.VETTED_PROVIDER


def test_reject_invalid_url() -> None:
    service = LeadIngestionService()

    with pytest.raises(ValueError, match="profile_url"):
        service.ingest(
            provider_name="proxycurl",
            leads=[
                InboundLead(
                    full_name="Jane Doe",
                    title="Head of Sales",
                    company="Acme Inc",
                    profile_url="not-a-url",
                    source=DataSource.OFFICIAL_API,
                )
            ],
        )


def test_reject_empty_batch() -> None:
    service = LeadIngestionService()

    with pytest.raises(ValueError, match="at least one lead"):
        service.ingest(provider_name="proxycurl", leads=[])
