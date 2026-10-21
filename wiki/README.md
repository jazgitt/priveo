# Priveo wiki

**Priveo** is a car-care product for housing societies, combining vehicle subscriptions, separately purchased services, crew execution and administrative operations. This wiki describes the product and its supporting software using repository requirements, implementation and recorded verification as references. Start with [Priveo](Priveo.md) for the product overview.[^1]

| Wiki information | Value |
|---|---|
| Scope | Product, operations, engineering and proposed extensions |
| Evidence reviewed | 20 October 2026 |
| Format | Linked Markdown articles with numbered references |
| Article limit | 2,000 words, including navigation and references |
| Editorial policy | [Editorial guidelines](Editorial_guidelines.md) |

## Contents

### Product and customer experience

| Article | Coverage |
|---|---|
| [Priveo](Priveo.md) | Service model, audiences and end-to-end lifecycle |
| [Customer app](Customer_app.md) | Onboarding, navigation and account experience |
| [Identity and access](Identity_and_access.md) | Login, verification, roles and sessions |
| [Vehicles and societies](Vehicles_and_societies.md) | Ownership, parking, catalogue and imports |
| [Subscriptions](Subscriptions.md) | Plans, activation, billing cycles and renewal |
| [Payments and invoices](Payments_and_invoices.md) | UPI confirmation, debt and GST records |
| [Add-on services](Add_on_services.md) | Catalogue, Deep Spa and standalone bookings |
| [Calendar and history](Calendar_and_history.md) | Date views, service details and imported history |
| [Skips and pauses](Skips_and_pauses.md) | Deadlines, covered dates and extensions |
| [Support and feedback](Support_and_feedback.md) | Complaints, ratings, feedback and check-ins |

### Service operations

| Article | Coverage |
|---|---|
| [Crew app](Crew_app.md) | Job cards, roles and manager actions |
| [Workforce management](Workforce_management.md) | Hours, exceptions, trainees and society moves |
| [Scheduling and capacity](Scheduling_and_capacity.md) | Solver, drafts, freeze and late changes |
| [Service execution and proof](Service_execution_and_proof.md) | Checklists, media and completion |
| [Operations and recovery](Operations_and_recovery.md) | Missed jobs, operational skips and reassignment |
| [Admin portal](Admin_portal.md) | Web administration and mobile quick actions |
| [Site setup](Site_setup.md) | Reference data, settings and historical snapshots |
| [Notifications](Notifications.md) | Customer preferences, crew/admin alerts and jobs |

### Engineering and governance

| Article | Coverage |
|---|---|
| [Architecture](Architecture.md) | Components, repository and integration boundaries |
| [API and data model](API_and_data_model.md) | Contracts, entities, persistence and migrations |
| [Design system](Design_system.md) | Brand, themes, accessibility and shared UI |
| [Analytics and privacy](Analytics_and_privacy.md) | PostHog, replay, notices and unresolved decisions |
| [Development](Development.md) | Local setup, generated files and configuration |
| [Testing](Testing.md) | Suites, fixtures, coverage and evidence limits |
| [Deployment and hosting](Deployment_and_hosting.md) | Development hosting, AWS target and release work |
| [Security](Security.md) | Existing controls and documented backlog |
| [Requirements and roadmap](Requirements_and_roadmap.md) | Decisions, status tracking and remaining work |
| [Mani Bond](Mani_Bond.md) | Proposed Founder assistant and phased autonomy |
| [Glossary](Glossary.md) | Domain and technical terminology |
| [Editorial guidelines](Editorial_guidelines.md) | Article structure, citations and maintenance |

## Reading the evidence

An article may describe a **requirement**, an **implementation**, a **recorded test result**, or a **proposal**. These are different claims. An implemented feature is not automatically deployed or verified with real providers. The 20 October test report is newer than several repository summaries and explicitly excludes device, hosted database and live-provider validation.[^2]

Follow inline references to the source documents or code. Requirement identifiers in reference notes locate the relevant rows without depending on line numbers. The wiki is a project knowledge base; it makes no claim to be an independently sourced Wikipedia publication.

## References

[^1]: [Project README](../README.md), product summary; [customer requirements](../docs/reqs/customer-app-functional-requirements.md), scope and business rules.
[^2]: [Test report, 20 October 2026](../docs/testing/test-report-2026-10-20.md), summary and exclusions.

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
