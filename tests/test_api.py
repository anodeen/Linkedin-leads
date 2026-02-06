import pytest

from app.main import LeadIngestionService
from app.models import DataSource, InboundLead
from app.scoring import ICPRuleConfig


def test_ingest_and_list_leads() -> None:
    service = LeadIngestionService()

    response = service.ingest(
        provider_name="proxycurl",
        leads=[
            InboundLead(
                full_name="Jane Doe",
                title="Head of Sales",
                company="Acme B2B SaaS",
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


def test_score_lead_returns_breakdown() -> None:
    service = LeadIngestionService()
    ingest_response = service.ingest(
        provider_name="proxycurl",
        leads=[
            InboundLead(
                full_name="Jane Doe",
                title="Head of Sales",
                company="Acme B2B SaaS",
                profile_url="https://www.linkedin.com/in/jane-doe",
                source=DataSource.OFFICIAL_API,
            )
        ],
    )

    result = service.score_lead(ingest_response.lead_ids[0])

    assert result.score == 100
    assert len(result.breakdown) == 4
    assert all(item.matched for item in result.breakdown)


def test_score_lead_with_custom_icp_config() -> None:
    service = LeadIngestionService()
    service.configure_icp(
        ICPRuleConfig(
            title_keywords=("revops",),
            company_keywords=("fintech",),
            title_match_points=50,
            company_match_points=20,
            linkedin_profile_points=10,
            completeness_points=10,
        )
    )
    ingest_response = service.ingest(
        provider_name="proxycurl",
        leads=[
            InboundLead(
                full_name="John Smith",
                title="RevOps Manager",
                company="Atlas Fintech",
                profile_url="https://www.linkedin.com/in/john-smith",
                source=DataSource.VETTED_PROVIDER,
            )
        ],
    )

    result = service.score_lead(ingest_response.lead_ids[0])

    assert result.score == 90
    assert result.breakdown[0].rule == "title_keyword_match"
    assert result.breakdown[0].points == 50


def test_score_lead_not_found() -> None:
    service = LeadIngestionService()

    with pytest.raises(ValueError, match="not found"):
        service.score_lead(999)
