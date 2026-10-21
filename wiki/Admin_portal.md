# Admin portal

The **admin portal** is Priveo's React web application for full product administration. It complements a limited set of administrator quick actions in the mobile application. Its current source directory is `apps/web`, despite older architecture material using `apps/admin-web`.[^1][^2]

## Functional scope

| Area | Administrative responsibility |
|---|---|
| Customers and vehicles | Create/edit records, onboarding, imports and session control |
| Subscriptions | Activate, choose start date, inactivate and reactivate |
| Crew | Onboard, roles, hours, pairing, exceptions and society moves |
| Schedule | Run, review, edit, freeze/unfreeze and handle unplaced work |
| Payments | Review receipt, set status and issue invoices |
| Service operations | Operational skips and missed-job outcomes |
| Support | Complaints, notes, feedback, ratings and check-ins |
| Site Setup and Settings | Catalogue/reference data and configurable policies |
| Audit and alerts | Review changes, notifications and operational exceptions |

These areas are defined in the administrator requirements; the table is a scope map rather than a statement that every acceptance condition has been verified.[^1]

## Lists and site context

The portal supports society/site context and uses filters, summary tiles and status counts for major operational lists. Customer and subscription lists have table/tile views in the requirements. Payments summarize count and amount by status; complaints summarize status and overdue counts.[^1]

The reference-data area is named Site Setup. The add-on request page is named Add on Service Requests. Settings groups are separate tabs, including alert email and automatic-planning controls.[^1]

## Mobile quick actions

Administrator mobile scope includes alerts, payment status confirmation, read-only schedules/Needs scheduling, operational skips, missed-job outcomes and customer skip/pause actions. It also includes selected customer, complaint, feedback, capacity, crew-exception and add-on reads/actions.[^1]

Complex transactions remain web-only: customer/vehicle creation, full subscription settings, crew onboarding and credential management, catalogue editing, schedule planning/freezing, invoice generation and audit views. The existence of a mobile read screen does not imply full web-equivalent editing.[^1]

## Interaction and access

The portal uses shared UI components, confirmation dialogs, mutation handling and task presentation for longer work. Authentication uses a cookie session and CSRF controls, with a 60-minute inactivity rule.[^3][^4]

The Audit page explicitly asks for Refresh, loads the last 1,000 events and pages them in groups of 50. Analytics uses the project's PostHog EU setup, with autocapture and release replay off under the latest owner decisions.[^1][^5]

## See also

- [Site setup](Site_setup.md)
- [Identity and access](Identity_and_access.md)
- [Design system](Design_system.md)

## References

[^1]: [Admin requirements](../docs/reqs/admin-functional-requirements.md), ADM-ACC, list summaries, ADM-REF-07, ADM-ADD-13 and ADM-SET.
[^2]: [Portal package](../apps/web/package.json); [portal shell](../apps/web/src/Shell.tsx).
[^3]: [Portal UI review](../docs/design/admin-portal-ui-review.md); [project conventions](../CLAUDE.md), shared portal blocks.
[^4]: [Web session implementation](../services/api/app/platform/websession.py); [web authentication](../services/api/app/webauth/router.py).
[^5]: [Owner decisions, 19 October](../docs/reqs/owner-decisions-2026-10-19.md), portal analytics.

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
