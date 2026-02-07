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
