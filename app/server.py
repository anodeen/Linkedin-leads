from dataclasses import asdict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .main import LeadIngestionService
from .messaging import MessageCTA, MessageGenerationControls, MessageTemplate, MessageTone
from .models import DataSource, InboundLead


class InboundLeadPayload(BaseModel):
    full_name: str = Field(min_length=2)
    title: str = Field(min_length=2)
    company: str = Field(min_length=2)
    profile_url: str
    source: DataSource


class IngestPayload(BaseModel):
    provider_name: str = Field(min_length=2)
    leads: list[InboundLeadPayload] = Field(min_length=1)


class MessageControlsPayload(BaseModel):
    tone: MessageTone
    template: MessageTemplate
    cta: MessageCTA


app = FastAPI(title="Linkedin Leads Service", version="0.1.0")
service = LeadIngestionService()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/leads/ingest")
def ingest(payload: IngestPayload) -> dict:
    try:
        response = service.ingest(
            provider_name=payload.provider_name,
            leads=[
                InboundLead(
                    full_name=item.full_name,
                    title=item.title,
                    company=item.company,
                    profile_url=item.profile_url,
                    source=item.source,
                )
                for item in payload.leads
            ],
        )
        return asdict(response)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/leads")
def list_leads() -> list[dict]:
    return [asdict(item) for item in service.list_leads()]


@app.post("/v1/leads/{lead_id}/draft")
def generate_draft(lead_id: int, controls: MessageControlsPayload) -> dict:
    try:
        draft = service.generate_message_draft(
            lead_id=lead_id,
            controls=MessageGenerationControls(
                tone=controls.tone,
                template=controls.template,
                cta=controls.cta,
            ),
        )
        return {
            "subject": draft.subject,
            "body": draft.body,
            "controls": asdict(draft.controls),
            "personalization": [asdict(item) for item in draft.personalization],
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
