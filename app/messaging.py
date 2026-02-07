from dataclasses import dataclass
from enum import Enum

from .models import Lead


class MessageTone(str, Enum):
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    DIRECT = "direct"


class MessageTemplate(str, Enum):
    INTRO = "intro"
    FOLLOW_UP = "follow_up"


class MessageCTA(str, Enum):
    BOOK_CALL = "book_call"
    REPLY = "reply"


@dataclass(slots=True)
class MessageGenerationControls:
    tone: MessageTone
    template: MessageTemplate
    cta: MessageCTA


@dataclass(slots=True)
class PersonalizationEvidence:
    token: str
    value: str
    source: str
    captured_at: str
    confidence: float


@dataclass(slots=True)
class MessageDraft:
    subject: str
    body: str
    controls: MessageGenerationControls
    personalization: list[PersonalizationEvidence]


class MessageDraftGenerator:
    """PRD Step 3: deterministic draft generation with configurable controls."""

    def generate(self, lead: Lead, controls: MessageGenerationControls) -> MessageDraft:
        greeting = self._greeting_for_tone(controls.tone)
        template_line = self._template_line(controls.template, lead)
        cta_line = self._cta_line(controls.cta)

        subject = self._subject_for_template(controls.template, lead)
        body = (
            f"{greeting} {lead.full_name},\n\n"
            f"{template_line}\n\n"
            f"{cta_line}\n\n"
            "Best,\n"
            "Your SDR Team"
        )

        personalization = [
            PersonalizationEvidence(
                token="full_name",
                value=lead.full_name,
                source="lead_ingestion",
                captured_at=lead.created_at.isoformat(),
                confidence=0.99,
            ),
            PersonalizationEvidence(
                token="title",
                value=lead.title,
                source="lead_ingestion",
                captured_at=lead.created_at.isoformat(),
                confidence=0.95,
            ),
            PersonalizationEvidence(
                token="company",
                value=lead.company,
                source="lead_ingestion",
                captured_at=lead.created_at.isoformat(),
                confidence=0.95,
            ),
            PersonalizationEvidence(
                token="profile_url",
                value=lead.profile_url,
                source="lead_ingestion",
                captured_at=lead.created_at.isoformat(),
                confidence=0.9,
            ),
        ]

        return MessageDraft(subject=subject, body=body, controls=controls, personalization=personalization)

    def _greeting_for_tone(self, tone: MessageTone) -> str:
        if tone == MessageTone.FRIENDLY:
            return "Hi"
        if tone == MessageTone.DIRECT:
            return "Hello"
        return "Good day"

    def _template_line(self, template: MessageTemplate, lead: Lead) -> str:
        if template == MessageTemplate.FOLLOW_UP:
            return (
                f"I wanted to follow up because leaders in roles like {lead.title} at {lead.company} "
                "often ask us how to improve outbound performance with less manual work."
            )
        return (
            f"I noticed your work as {lead.title} at {lead.company} and thought a brief intro "
            "might be relevant to your growth goals."
        )

    def _cta_line(self, cta: MessageCTA) -> str:
        if cta == MessageCTA.BOOK_CALL:
            return "Would you be open to a 15-minute call next week to compare approaches?"
        return "If this is relevant, just reply and I can share a short tailored plan."

    def _subject_for_template(self, template: MessageTemplate, lead: Lead) -> str:
        if template == MessageTemplate.FOLLOW_UP:
            return f"Following up for {lead.company}"
        return f"Intro idea for {lead.company}"
