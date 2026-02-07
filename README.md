# Linkedin-leads

Starter implementation for an AI-powered lead generation and outreach platform.

## Current development stage
We have started the product build from the PRD roadmap with:
- **Step 1**: compliance-first ingestion (official APIs / vetted providers only).
- **Step 2**: ICP-configurable rule-based scoring with transparent score breakdown.
- **Step 3**: controlled draft generation scaffold (tone/template/CTA + personalization evidence metadata).
- **Step 4**: mandatory human approval workflow with send-blocking until an approved revision exists.
- **Step 5**: email outbound send scaffold with delivery telemetry event tracking.
- **Step 6**: manager dashboard snapshot API for activity and funnel metrics.
- **Step 7**: CRM outcome syncing and scoring-quality snapshot metrics.
- **Step 8**: append-only audit trail for key compliance-sensitive workflow actions.

See `docs/IMPLEMENTATION_PLAN.md` for the full step-by-step plan.

## Run tests
```bash
pytest
```
