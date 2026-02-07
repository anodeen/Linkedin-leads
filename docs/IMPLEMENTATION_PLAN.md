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

## Step 5 — One outbound channel and telemetry
- Add one send channel integration (email-first).
- Store send events, delivery, bounce, and complaint metrics.

## Step 6 — Basic manager dashboard API
- Implement reporting endpoints for activity and conversion funnel.

## Step 7 — Single CRM sync for outcomes
- Add one CRM connector for outcome labels.
- Feed outcome data into scoring quality measurement.
