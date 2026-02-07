# Implementation Plan (PRD Step-by-Step)

This document turns the reviewed PRD into execution phases and tracks what has been started.

## Step 1 — Compliance-first lead ingestion (completed)
- Build ingestion API that only accepts **official API** or **vetted provider** sources.
- Keep scraping out of the customer-facing flow.
- Deliver persisted lead records.

**Status:** ✅ Completed in repository service layer.

## Step 2 — ICP-configurable rule-based scoring (completed)
- Add ICP rule configuration model.
- Implement deterministic scoring with transparent rule breakdown.
- Expose score service method and explanation metadata.

**Status:** ✅ Completed in repository service layer.

## Step 3 — LLM draft generation with controls (completed: deterministic scaffold)
- Add message generation method with tone/template/CTA controls.
- Return source-backed personalization fields and confidence markers.
- Keep implementation deterministic now, ready to swap with LLM provider later.

**Status:** ✅ Completed as a deterministic service scaffold with controls + evidence metadata.

## Step 4 — Mandatory human approval before sending (completed)
- Add approval workflow entities and service methods.
- Block send operation unless an approved revision exists.

**Status:** ✅ Completed with draft submission/review and send-guard enforcement.

## Step 5 — One outbound channel and telemetry (completed)
- Add email send integration method for approved drafts only.
- Store send and delivery events (sent/delivered/bounced/complaint).

**Status:** ✅ Completed with email channel + delivery telemetry event log.

## Step 6 — Basic manager dashboard API (completed)
- Implement activity and conversion funnel reporting snapshot.
- Aggregate ingest/approval/delivery telemetry into manager-facing metrics.

**Status:** ✅ Completed with dashboard snapshot builder and service accessor.

## Step 7 — Single CRM sync for outcomes (completed)
- Add one CRM connector path for outcome labels.
- Feed labeled outcomes into scoring quality measurement.

**Status:** ✅ Completed with CRM outcome sync + scoring quality snapshot metrics.

## Step 8 — Compliance hardening: audit trail (completed)
- Add append-only audit logging for key state changes.
- Capture ingestion, review, send, delivery, and CRM sync actions.

**Status:** ✅ Completed with service-level audit event history.

## Step 9 — DSAR deletion workflow (completed)
- Add lead deletion request flow.
- Propagate deletion across approvals, delivery telemetry, CRM outcomes, and lead records.

**Status:** ✅ Completed with purge summary and audit trail event.


## Step 10 — Retention policy enforcement (completed)
- Add retention policy execution to purge aged records across leads, approvals, telemetry, CRM outcomes, and audit events.
- Emit an audit event for retention policy runs with purge counts.

**Status:** ✅ Completed with service-level retention sweep and verification tests.


## Step 11 — Compliance posture snapshot (completed)
- Add compliance reporting snapshot that rolls up governance/control metrics.
- Surface DSAR + retention execution indicators for readiness checks.

**Status:** ✅ Completed with service-level compliance snapshot aggregation.


## Step 12 — Deployment packaging (completed)
- Add deployable HTTP app entrypoint and container runtime configuration.
- Provide Docker and Compose setup for local/prod-style deployment.

**Status:** ✅ Completed with FastAPI server + Docker packaging.
