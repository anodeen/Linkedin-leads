import pytest

from app.approval import ApprovalStatus
from app.main import LeadIngestionService
from app.messaging import MessageCTA, MessageGenerationControls, MessageTemplate, MessageTone
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


def test_generate_message_draft_with_controls() -> None:
    service = LeadIngestionService()
    ingest_response = service.ingest(
        provider_name="proxycurl",
        leads=[
            InboundLead(
                full_name="Alex Rivera",
                title="VP Sales",
                company="Orbit SaaS",
                profile_url="https://www.linkedin.com/in/alex-rivera",
                source=DataSource.OFFICIAL_API,
            )
        ],
    )

    controls = MessageGenerationControls(
        tone=MessageTone.FRIENDLY,
        template=MessageTemplate.INTRO,
        cta=MessageCTA.REPLY,
    )

    draft = service.generate_message_draft(ingest_response.lead_ids[0], controls)

    assert draft.subject == "Intro idea for Orbit SaaS"
    assert draft.body.startswith("Hi Alex Rivera")
    assert "just reply" in draft.body
    assert draft.controls.tone == MessageTone.FRIENDLY
    assert len(draft.personalization) == 4
    assert draft.personalization[0].token == "full_name"


def test_generate_message_draft_not_found() -> None:
    service = LeadIngestionService()

    controls = MessageGenerationControls(
        tone=MessageTone.PROFESSIONAL,
        template=MessageTemplate.FOLLOW_UP,
        cta=MessageCTA.BOOK_CALL,
    )

    with pytest.raises(ValueError, match="not found"):
        service.generate_message_draft(999, controls)


def test_send_blocked_until_approved_revision_exists() -> None:
    service = LeadIngestionService()
    ingest_response = service.ingest(
        provider_name="proxycurl",
        leads=[
            InboundLead(
                full_name="Mina Patel",
                title="Head of Revenue",
                company="Nova SaaS",
                profile_url="https://www.linkedin.com/in/mina-patel",
                source=DataSource.OFFICIAL_API,
            )
        ],
    )
    lead_id = ingest_response.lead_ids[0]

    controls = MessageGenerationControls(
        tone=MessageTone.PROFESSIONAL,
        template=MessageTemplate.FOLLOW_UP,
        cta=MessageCTA.BOOK_CALL,
    )
    draft = service.generate_message_draft(lead_id, controls)

    with pytest.raises(ValueError, match="approved revision"):
        service.assert_send_allowed(lead_id)

    approval = service.submit_draft_for_approval(lead_id, draft)
    assert approval.status == ApprovalStatus.PENDING

    reviewed = service.review_draft(
        revision_id=approval.revision_id,
        reviewer="SDR Manager",
        approve=True,
        review_notes="Looks compliant and on-brand",
    )
    assert reviewed.status == ApprovalStatus.APPROVED

    service.assert_send_allowed(lead_id)


def test_rejected_revision_does_not_unlock_send() -> None:
    service = LeadIngestionService()
    ingest_response = service.ingest(
        provider_name="proxycurl",
        leads=[
            InboundLead(
                full_name="Lena Park",
                title="VP Sales",
                company="Aster AI",
                profile_url="https://www.linkedin.com/in/lena-park",
                source=DataSource.VETTED_PROVIDER,
            )
        ],
    )
    lead_id = ingest_response.lead_ids[0]

    draft = service.generate_message_draft(
        lead_id,
        MessageGenerationControls(
            tone=MessageTone.DIRECT,
            template=MessageTemplate.INTRO,
            cta=MessageCTA.REPLY,
        ),
    )

    approval = service.submit_draft_for_approval(lead_id, draft)
    reviewed = service.review_draft(
        revision_id=approval.revision_id,
        reviewer="AB",
        approve=False,
        review_notes="Needs safer claims",
    )
    assert reviewed.status == ApprovalStatus.REJECTED

    with pytest.raises(ValueError, match="approved revision"):
        service.assert_send_allowed(lead_id)
