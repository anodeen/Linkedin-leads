import pytest

from app.approval import ApprovalStatus
from app.delivery import DeliveryEventType
from app.crm import OutcomeStatus
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


def test_send_approved_message_and_record_telemetry() -> None:
    service = LeadIngestionService()
    ingest_response = service.ingest(
        provider_name="proxycurl",
        leads=[
            InboundLead(
                full_name="Sara Kim",
                title="Sales Director",
                company="Polaris SaaS",
                profile_url="https://www.linkedin.com/in/sara-kim",
                source=DataSource.OFFICIAL_API,
            )
        ],
    )
    lead_id = ingest_response.lead_ids[0]

    draft = service.generate_message_draft(
        lead_id,
        MessageGenerationControls(
            tone=MessageTone.PROFESSIONAL,
            template=MessageTemplate.INTRO,
            cta=MessageCTA.BOOK_CALL,
        ),
    )
    approval = service.submit_draft_for_approval(lead_id, draft)
    service.review_draft(approval.revision_id, reviewer="Manager", approve=True)

    sent_event = service.send_approved_message(lead_id, recipient_email="sara.kim@polaris.example")
    assert sent_event.event_type == DeliveryEventType.SENT

    delivered_event = service.record_delivery_event(
        lead_id=lead_id,
        event_type=DeliveryEventType.DELIVERED,
        recipient_email="sara.kim@polaris.example",
    )
    assert delivered_event.event_type == DeliveryEventType.DELIVERED

    lead_events = service.list_delivery_events(lead_id=lead_id)
    assert len(lead_events) == 2
    assert lead_events[0].event_type == DeliveryEventType.SENT
    assert lead_events[1].event_type == DeliveryEventType.DELIVERED


def test_send_rejects_invalid_email() -> None:
    service = LeadIngestionService()
    ingest_response = service.ingest(
        provider_name="proxycurl",
        leads=[
            InboundLead(
                full_name="Nora Yu",
                title="VP Revenue",
                company="Helios B2B",
                profile_url="https://www.linkedin.com/in/nora-yu",
                source=DataSource.VETTED_PROVIDER,
            )
        ],
    )
    lead_id = ingest_response.lead_ids[0]

    draft = service.generate_message_draft(
        lead_id,
        MessageGenerationControls(
            tone=MessageTone.DIRECT,
            template=MessageTemplate.FOLLOW_UP,
            cta=MessageCTA.REPLY,
        ),
    )
    approval = service.submit_draft_for_approval(lead_id, draft)
    service.review_draft(approval.revision_id, reviewer="Manager", approve=True)

    with pytest.raises(ValueError, match="valid email"):
        service.send_approved_message(lead_id, recipient_email="invalid-email")


def test_manager_dashboard_snapshot_activity_and_funnel() -> None:
    service = LeadIngestionService()

    first = service.ingest(
        provider_name="proxycurl",
        leads=[
            InboundLead(
                full_name="A One",
                title="Sales Director",
                company="Alpha SaaS",
                profile_url="https://www.linkedin.com/in/a-one",
                source=DataSource.OFFICIAL_API,
            )
        ],
    )
    second = service.ingest(
        provider_name="proxycurl",
        leads=[
            InboundLead(
                full_name="B Two",
                title="VP Sales",
                company="Beta SaaS",
                profile_url="https://www.linkedin.com/in/b-two",
                source=DataSource.VETTED_PROVIDER,
            )
        ],
    )

    lead_1 = first.lead_ids[0]
    lead_2 = second.lead_ids[0]

    draft_1 = service.generate_message_draft(
        lead_1,
        MessageGenerationControls(
            tone=MessageTone.PROFESSIONAL,
            template=MessageTemplate.INTRO,
            cta=MessageCTA.BOOK_CALL,
        ),
    )
    draft_2 = service.generate_message_draft(
        lead_2,
        MessageGenerationControls(
            tone=MessageTone.DIRECT,
            template=MessageTemplate.FOLLOW_UP,
            cta=MessageCTA.REPLY,
        ),
    )

    rev_1 = service.submit_draft_for_approval(lead_1, draft_1)
    rev_2 = service.submit_draft_for_approval(lead_2, draft_2)

    service.review_draft(rev_1.revision_id, reviewer="Manager", approve=True)
    service.review_draft(rev_2.revision_id, reviewer="Manager", approve=False)

    service.send_approved_message(lead_1, recipient_email="a.one@alpha.example")
    service.record_delivery_event(lead_1, DeliveryEventType.DELIVERED, "a.one@alpha.example")
    service.record_delivery_event(lead_1, DeliveryEventType.COMPLAINT, "a.one@alpha.example")

    dashboard = service.get_manager_dashboard()

    assert dashboard.activity.leads_ingested == 2
    assert dashboard.activity.drafts_submitted == 2
    assert dashboard.activity.drafts_reviewed == 2
    assert dashboard.activity.approved_drafts == 1
    assert dashboard.activity.rejected_drafts == 1

    assert dashboard.funnel.leads_total == 2
    assert dashboard.funnel.leads_with_approved_draft == 1
    assert dashboard.funnel.messages_sent == 1
    assert dashboard.funnel.messages_delivered == 1
    assert dashboard.funnel.messages_bounced == 0
    assert dashboard.funnel.complaints == 1


def test_crm_outcome_sync_and_scoring_quality_snapshot() -> None:
    service = LeadIngestionService()

    batch = service.ingest(
        provider_name="proxycurl",
        leads=[
            InboundLead(
                full_name="Winner One",
                title="Head of Sales",
                company="Gamma B2B SaaS",
                profile_url="https://www.linkedin.com/in/winner-one",
                source=DataSource.OFFICIAL_API,
            ),
            InboundLead(
                full_name="Loser Two",
                title="Associate",
                company="Local Shop",
                profile_url="https://www.linkedin.com/in/loser-two",
                source=DataSource.VETTED_PROVIDER,
            ),
        ],
    )

    lead_won, lead_lost = batch.lead_ids

    synced = service.sync_crm_outcome(lead_won, status=OutcomeStatus.WON, deal_value=25000)
    assert synced.crm_name == "hubspot"

    service.sync_crm_outcome(lead_lost, status=OutcomeStatus.LOST, deal_value=0)

    quality = service.get_scoring_quality_snapshot(high_score_threshold=70)

    assert quality.total_labeled == 2
    assert quality.won_count == 1
    assert quality.high_score_count == 1
    assert quality.high_score_win_rate == 1.0

    outcomes = service.list_crm_outcomes()
    assert len(outcomes) == 2


def test_audit_log_captures_key_workflow_events() -> None:
    service = LeadIngestionService()

    ingest = service.ingest(
        provider_name="proxycurl",
        leads=[
            InboundLead(
                full_name="Audit User",
                title="Head of Sales",
                company="Audit SaaS",
                profile_url="https://www.linkedin.com/in/audit-user",
                source=DataSource.OFFICIAL_API,
            )
        ],
    )
    lead_id = ingest.lead_ids[0]

    draft = service.generate_message_draft(
        lead_id,
        MessageGenerationControls(
            tone=MessageTone.PROFESSIONAL,
            template=MessageTemplate.INTRO,
            cta=MessageCTA.BOOK_CALL,
        ),
    )
    approval = service.submit_draft_for_approval(lead_id, draft)
    service.review_draft(approval.revision_id, reviewer="Manager", approve=True)
    service.send_approved_message(lead_id, recipient_email="audit.user@audit.example")
    service.sync_crm_outcome(lead_id, status=OutcomeStatus.WON, deal_value=10000)

    actions = [event.action for event in service.list_audit_events()]

    assert "lead_batch_ingested" in actions
    assert "draft_submitted_for_approval" in actions
    assert "draft_reviewed" in actions
    assert "message_sent" in actions
    assert "crm_outcome_synced" in actions
