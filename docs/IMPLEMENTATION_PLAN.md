# Implementation Plan (PRD Step-by-Step)

This document turns the reviewed PRD into execution phases and tracks what has been started.

## Step 1 — Compliance-first lead ingestion (started)
- Build ingestion API that only accepts **official API** or **vetted provider** sources.
- Keep scraping out of the customer-facing flow.
- Deliver health check and persisted lead records.

**Status:** ✅ In progress and bootstrapped in this repository.

## Step 2 — ICP-configurable rule-based scoring
- Add ICP rule configuration model.
- Implement deterministic scoring with transparent rule breakdown.
- Expose score API and score explanation metadata.

## Step 3 — LLM draft generation with controls
- Add message generation endpoint with tone/template/CTA controls.
- Return source-backed personalization fields and confidence markers.

## Step 4 — Mandatory human approval before sending
- Add approval workflow entities and endpoints.
- Block send operation unless an approved revision exists.

## Step 5 — One outbound channel and telemetry
- Add one send channel integration (email-first).
- Store send events, delivery, bounce, and complaint metrics.

## Step 6 — Basic manager dashboard API
- Implement reporting endpoints for activity and conversion funnel.

## Step 7 — Single CRM sync for outcomes
- Add one CRM connector for outcome labels.
- Feed outcome data into scoring quality measurement.
