# Mani Bond

**Mani Bond**, also called **Dr Bond**, is a specified Founder-facing Chief of Staff assistant for Priveo. The specification uses they/them pronouns and names business, technology, operations/HR and finance as functional domains. The repository contains requirements and architecture proposals; the solution plan explicitly does not include implementation or infrastructure changes. The initial assessment provides earlier planning context.[^1][^2][^3]

| Attribute | Specified or proposed direction |
|---|---|
| Intended user | Founder and CEO |
| Initial interface | Private page within the administrator portal |
| Initial capability | Read, explain, report and recommend |
| Initial voice | English/Hindi push-to-talk |
| Processing boundary | India-only under the solution plan |
| Delivery model | Crawl, Walk, Run |

## Purpose and evidence

Mani acts for the Founder rather than impersonating them. Messages and commitments in the Founder's name require specific authorization. Answers should distinguish stale, missing or conflicting data rather than inventing certainty.[^1]

The proposed solution separates indexed documents/code, controlled queries for current business facts and attributable Founder-provided memory. Citations retain source titles, requirement IDs, paths, commits and timestamps. Financial totals and scheduling calculations remain backend computations that the assistant explains.[^2]

## Delivery phases

**Crawl** provides knowledge retrieval, current read tools, reports and recommendations. The proposed first usable release includes English/Hindi voice. It has no tools that modify Priveo business records.[^2]

**Walk** adds an approved action catalogue. A concrete proposal displays affected records, before/after changes and consequences. Approval is bound to the proposal, Founder session, versions and a short expiry; the backend rechecks permissions and state before audited, idempotent execution.[^2]

**Run** adds bounded autonomy through a versioned Founder-approved policy. The allowed action list begins empty and requires explicit limits, expiry and revocation. Missing approval is not treated as permission.[^2]

Finance remains read-only in the plan. Sensitive HR decisions, money movement and permission changes are excluded, and customer-facing commitments remain gated.[^2]

## Proposed architecture

The plan reuses React/FastAPI and existing business services, with one orchestrator and typed tools. It proposes PostgreSQL text/vector retrieval, private source snapshots, durable queue-backed workers, monitoring and scheduled refreshes. It recommends an AWS Bedrock India route and regional voice services, subject to destination, access, quota and quality checks at implementation time.[^2]

These are attributed design proposals, not fresh provider-availability claims or a deployed service inventory. The plan calls for preventing automatic processing fallback outside India.[^2]

## Privacy and acceptance

Founder authorization codes must stay out of model context, audio, transcripts, replay, analytics and logs. The proposed interface disables replay and permits content-free usage metrics. That is stricter than the current general product test-replay policy and requires separate implementation.[^2]

Acceptance covers Founder-only access, cited factual answers, stale/conflicting sources, voice transcription review, non-modifying Crawl behavior, approval replay/expiry/concurrency, audit linkage and India-boundary checks. Effort and retention values in the plan are provisional defaults, not operational commitments.[^2]

## See also

- [Requirements and roadmap](Requirements_and_roadmap.md)
- [Architecture](Architecture.md)
- [Analytics and privacy](Analytics_and_privacy.md)

## References

[^1]: [Mani Bond specification v3](../docs/agent/mani-bond-spec_final.md), identity, principles, functional areas and autonomy.
[^2]: [Mani Bond architecture](../docs/agent/agent-architecure.md), the single architecture document: architecture, stack, phases, privacy and acceptance.
[^3]: [Mani Bond final spec](../docs/agent/mani-bond-spec_final.md), requirements.

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
