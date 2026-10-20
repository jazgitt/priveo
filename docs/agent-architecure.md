# Mani Bond: architecture assessment and implementation plan

Date: 20-Oct-2026  
Status: Proposed assessment and plan; implementation has not started.  
Audience: Founder, Claude, Codex and implementation engineers.  
Primary requirement source: [Mani Bond final spec v3](reqs/mani-bond-spec_final.md).

## 1. Assessment

Mani Bond is feasible within Priveo's existing architecture, but is a substantial new subsystem. The chat screen is a small part of the work. The main engineering effort is reliable knowledge retrieval, current business data, secure approvals, controlled execution and evidence that the assistant behaves correctly.

Mani is the Founder's Chief of Staff, created by Glowing Spoon. Always use they/them/their for Mani. They act for the Founder, never as the Founder. The initial channel is the Admin portal, accessible only to the Founder, with English and Hindi support.

This document records recommendations and estimates, not new owner decisions. The requirement spec and subsequent explicit owner decisions take precedence. Unresolved scope questions below must not silently become implementation assumptions. The request to write this document does not authorise implementation, deployment, migrations or external service provisioning.

## 2. Existing foundations and gaps

The assessment used static inspection of the repository; it does not establish deployed behaviour or a complete requirement audit. No tests, builds or migrations were run for this assessment.

| Area | Existing foundation | Additional work for Mani |
|---|---|---|
| Portal | React Admin portal, authenticated sessions and shared UI blocks | Founder-only assistant page, chat, sources, proposals, voice and history |
| Backend | FastAPI, SQLAlchemy and PostgreSQL architecture | Assistant orchestration, model integration and controlled business tools |
| Identity | Customer, crew and admin roles; session and CSRF checks | Explicit founder capability, checked on every assistant endpoint and task |
| Operations | Scheduling, OR-Tools planning, customer/crew management and service workflows | Read adapters and a bounded catalogue of proposal/execution tools |
| Finance | Payments, subscriptions and invoices | Read-only reporting; expense inputs and definitions for profitability |
| Audit | Existing domain audit records and payment/schedule events | Link assistant intent, exact approval, execution and result |
| Background work | Protected cron endpoints and notification patterns | Dependable refresh, monitoring, retries, deduplication and freshness tracking |
| AI and voice | No assistant, knowledge index or voice integration found in inspected code | New capabilities and provider configuration |

Relevant implementation references:

- `apps/web/src/auth/AuthContext.tsx`: portal authentication context.
- `services/api/app/platform/deps.py`: role checks, cookie authentication and CSRF protection.
- `services/api/app/identity/models.py`: existing login roles and sessions.
- `services/api/app/directory/models.py`: existing audit model.
- `services/api/app/billing/models.py`: payments, invoices and subscription events.
- `services/api/app/scheduling/`: scheduling services and planning rules.
- `services/api/app/notifications/cron.py`: existing background-job entry points.
- `services/api/pyproject.toml`: backend dependency baseline.
- [Current handoff](codex-handoff-plan.md), [tech stack](tech-stack.md) and [security backlog](security-backlog.md): existing integration and release constraints.

Existing code and deployed configuration must be rechecked before implementation. In particular, daily cron patterns do not establish near-real-time monitoring. Follow the project's decided AWS Mumbai hosting architecture; inspect current deployment before choosing how assistant workers run.

## 3. Proposed architecture

```text
Founder in Admin portal
  -> Founder authentication and access checks
  -> Mani conversation API
      -> Model adapter and persona
      -> Document/code retrieval with source references
      -> Controlled read tools for current business data
      -> Persistent, attributable memory
      -> Proposal generator
          -> Deterministic policy and approval checks
          -> Existing business services
          -> Execution result and linked audit

Background workers
  -> Source refresh and freshness records
  -> Operational checks and alert deduplication
  -> Founder digests and scheduled reports in the portal

Voice input/output
  -> English/Hindi transcription and speech
  -> Same conversation, access and approval boundaries
```

Start with an assistant module inside the existing FastAPI service and a page in the existing portal. Use a separate worker process where durable background execution is required. A separate assistant microservice is not necessary initially. Module names, schema and worker technology remain implementation proposals.

### Knowledge and live data

- Index approved requirements, documents and selected code/configuration. Exclude secrets, credentials and sensitive configuration values before indexing or sending content to a model.
- Record source identity, version or commit, ingestion time, refresh policy and refresh failures. Handle deletions and superseded documents.
- Retrieve document/code evidence for explanations. Query controlled live tools for current operational facts; do not use an old document index to answer today's schedule or payment state.
- Perform sums and business calculations in backend code. Define time periods, IST boundaries, payment versus revenue semantics and applicable exclusions.
- Show sources, the relevant data timestamp and limitations. Confidence should reflect evidence quality and completeness rather than an invented probability.
- Treat retrieved documents and database text as data, never as authority to change permissions or bypass approval.

### Memory and conversations

- Persist conversations and useful Founder-provided facts/preferences separately from retrieved business records.
- Store provenance and timestamps, with correction, deletion and retention controls.
- Distinguish confirmed facts, tentative inferences and unresolved questions. Do not silently promote an inference into a fact.
- Interpret continuous learning initially as refreshed knowledge and persistent memory, not automatic model retraining.
- Batch non-urgent questions. Missing answers must leave dependent changes pending; urgent escalation remains within the authorised channel.

### Founder-only access

The current `admin` role does not distinguish the Founder. Add an explicit founder capability or equivalent account binding, enforced server-side for chat, sources, history, voice, approvals, reports and background task ownership. Hiding a navigation item is insufficient. Mani must not grant or change their own permissions.

### Controlled tools

Expose narrow business functions with validated inputs and bounded outputs. Start with tools for operational summaries, schedules, missed jobs, crew availability, complaints, subscriptions and collections. Do not give the model unrestricted database writes, shell access or general admin credentials.

Reuse existing domain services and their validation. Refactor shared logic where necessary rather than duplicating scheduling or billing rules in assistant prompts. Keep finance read-only, including payment-status changes, unless a later explicit requirement changes that boundary.

### Approval and execution

Proposed state flow: draft -> awaiting approval -> approved -> executing -> succeeded/failed. Also support rejected, cancelled, expired and invalidated proposals.

1. Mani prepares a typed proposal with exact parameters, affected records, before/after effects, side effects and relevant data versions.
2. The Founder reviews the proposal in the portal.
3. A separate secure app control verifies the authorisation code. Store only a suitable verifier; never put the code in model context, memory, transcripts, analytics or logs. Support rotation, attempt limits and expiry.
4. The backend binds approval to the exact proposal, Founder identity, current session and a short validity period. Edited proposals require fresh approval.
5. Before execution, recheck access, policy, record versions and business constraints. Changed underlying data invalidates the approval and requires a new preview.
6. Execute with transactional protection and idempotency so retries cannot duplicate actions. Persist execution state and audit reliably with the business change; use a durable outbox for external side effects where necessary.
7. Show the result or failure, including partial external effects and recovery requirements. Do not promise universal rollback.

Example: reassigning an absent crew member's jobs must preview affected jobs, capacity, schedule state and customer notifications. Approval applies to that specific change, not an open-ended instruction to edit schedules later.

Money movement, sensitive HR decisions, irreversible/customer-facing commitments and permission changes must be blocked or handed to the Founder as specified. A code alone must not unlock a forbidden tool. Resolve ambiguous schedule side effects before enabling those tools.

For v1, keep code entry in the secure app control even when a proposal originates through voice. Speaking the secret risks recording it in transcripts or sending it to speech providers.

### Voice, monitoring and operations

- Support English and Hindi recognition and speech through a provider adapter. Test mixed-language speech, names, dates, amounts and interruption/cancellation.
- Start with explicit microphone activation; continuous ambient listening is not required by the spec.
- Use scheduled checks and change-triggered refreshes rather than continuously invoking a model. Invoke the model when interpretation or conversation is needed.
- Track refresh failures, job retries, model errors, latency, usage and costs. Add request/tool limits and a switch to disable action execution without losing read-only access.
- Keep proactive alerts, digests and reports Founder-only in the portal. Define what urgent escalation means when the Founder is offline; do not add email, WhatsApp or crew messaging by assumption.

## 4. Data dependencies and open scope decisions

| Decision | Why it matters |
|---|---|
| First-release boundary | Section 10 says full v1 scope, while Section 8 stages Crawl, Walk and Run. Agree exactly which capabilities ship first. |
| Initial action catalogue | Scheduling and data setup are broad. List the first permitted operations and their side effects. |
| Level 3 authorisation | AU-2 requires the code for every operation, while Level 3 allows pre-approved actions. Define whether code entry grants a policy or is required on each execution. |
| Crew-facing HR | Founder-only communication conflicts with Run's crew-facing HR. Treat it as a later access/channel change requiring a decision. |
| Customer-facing consequences | Scheduling may notify customers or create commitments. Clarify which approved actions are allowed and which remain Founder-executed. |
| Finance and profitability | No complete expense/payroll ledger was found in inspected code. Supply costs, allocation rules and reporting definitions before claiming profitability. |
| HR workflows | Define concrete tasks and inputs, such as policy drafts or staffing summaries. Sensitive personnel decisions remain with the Founder. |
| Refresh and alert targets | Define measurable per-source freshness and problem-to-alert targets, not only “near real time.” |
| Sources and retention | Identify connected repositories/documents, read permissions, conversation retention, audio retention and allowed provider data handling. |
| Acceptance questions | Supply a fixed set of business questions, expected evidence and accuracy targets. |
| Provider and operating budget | Select model/speech services after checking data requirements, quality, expected usage and current pricing. No provider is chosen here. |

Missing finance or HR inputs should be reported explicitly; their absence need not prevent useful operations and collections reporting.

## 5. Phased implementation plan

### Phase A: scope and foundation

- Resolve the first-release boundary, source inventory, Founder identity, initial tools and acceptance targets.
- Design assistant records, access checks, source tracking, retention and audit links.
- Select provider adapters and background execution compatible with the existing architecture.

Exit: a bounded backlog with explicit acceptance criteria. This foundation work is included in the Crawl estimate below.

### Phase B: Crawl, Levels 0 and 1

- Build Founder-only text chat, conversation history and persona behaviour.
- Import requirements and selected code/documents with refresh and citations.
- Add live read tools and deterministic business summaries.
- Add attributable memory, question digests and proposal previews with no domain writes.
- Establish the business-question evaluation and evidence/freshness checks.

Exit: the Founder can ask useful business, technology, operations and available-finance questions, see their evidence and receive draft recommendations. Domain actions remain unavailable. Audit/access foundations start here, not only in Walk.

### Phase C: English/Hindi voice

- Add speech input and output to the same conversation service.
- Validate language switching, names, numbers, cancellation and recovery.
- Keep secret entry outside speech and conversation handling.

Exit: practical English/Hindi interaction with the same access and policy boundaries as text. This work may overlap Crawl but is shown separately for effort planning.

### Phase D: Walk, Level 2

- Implement the agreed small catalogue of scheduling/data-setup actions.
- Add secure code verification, exact proposal approval, expiry, version checks and rotation.
- Implement durable execution, idempotency and linked intent/approval/result audit.
- Add scheduled portal reports and agreed operational alerts.

Exit: only specifically approved, permitted operations execute, and every executed action has a complete audit entry.

### Phase E: production hardening and acceptance

- Validate access isolation, secret redaction, prompt-injection resistance and policy enforcement.
- Test concurrent changes, duplicate requests, expired/replayed approvals, worker restart, provider outages and refresh failures.
- Verify PostgreSQL behaviour, deployment configuration, backups, monitoring and recovery.
- Run the agreed business evaluation and measure alert delay, action rejection and usage.

Exit: acceptance criteria pass in the intended deployment. Existing Priveo release gaps remain separate unless they directly block Mani.

### Phase F: Run, Level 3 and expanded scope

Define the pre-approved action policy, limits, revocation and pause controls before implementing autonomy. Estimate crew-facing HR and additional dialects only after their workflows, permissions and success criteria are agreed. Do not enable Run automatically after Walk.

## 6. Effort and operating costs

Preliminary estimates assume one experienced full-time engineer using AI-assisted development, timely Founder feedback and access to required services. They include feature testing and integration but exclude unrelated Priveo release work, a new full accounting/payroll system and unspecified external connectors. These are planning ranges, not delivery commitments.

| Stage | Additional engineer-weeks |
|---|---:|
| Crawl, including scope/foundation | 4-6 |
| English/Hindi voice | 1-2 |
| Walk with a bounded action catalogue | 3-5 |
| Production hardening and acceptance | 2-3 |
| Total through Crawl + voice + Walk + hardening | 10-16 |
| Run | Estimate after scope definition |

Calendar time depends on availability, decision turnaround and external dependencies. The estimate should be revised after the initial backlog and source inventory are agreed.

Recurring costs include model input/output, speech minutes, indexing, storage, background execution and observability. A monetary estimate requires expected conversation volume, voice minutes, source size, refresh frequency and current provider pricing. No price quotes have been verified for this assessment.

## 7. Verification and success measures

- Use fixed, representative Founder questions with independently checked expected facts and sources. Include missing, stale and conflicting data.
- Verify financial totals and scheduling answers against deterministic backend results.
- Prove non-Founder accounts cannot access any assistant surface or its underlying data endpoints.
- Prove domain writes are impossible in Crawl and forbidden actions remain blocked even after code verification.
- Test proposal tampering, stale approvals, code rotation, repeated execution and audit consistency under failure.
- Test voice with actual English/Hindi samples, especially dates, names and amounts.
- Measure Founder hours saved, answer accuracy, problem-to-alert delay, complete action audits (target 100%) and rejected proposals.
- Follow repository testing and contract conventions for changed code; document separately what passed locally and what was verified live.

## 8. Handoff guidance for Claude and Codex

Read this plan together with the primary spec and current repository guidance. Preserve existing business rules and security requirements. Recheck implementation and deployment facts before relying on historical handoff notes. Distinguish owner decisions from proposals and unresolved questions.

Recommended starting point: agree a Crawl milestone across the four knowledge domains, with evidence and freshness indicators, then add a small Walk action catalogue after the assistant passes the business-question evaluation. Do not begin with unrestricted admin automation.
