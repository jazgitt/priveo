# API and data model

Priveo's **API and data model** provide a shared contract and persistent business records for mobile and web clients. The backend uses FastAPI, Pydantic, SQLAlchemy and Alembic, with PostgreSQL selected for application storage.[^1]

## API contract

The repository exports OpenAPI to `packages/api-contract/openapi.json`. The Flutter generator derives API models and calls from that file. The contract must be regenerated after backend schema changes, followed by dependent generated output. An architecture proposal for additional audience-specific schemas should not be confused with the currently exported artifact.[^2][^3]

Routes are versioned under `/v1` and grouped by function/audience, including authentication, customer, crew, administrator, public and web-session paths. Internal scheduled jobs are deliberately excluded from the public OpenAPI schema. Exact paths, fields and methods should be read from the exported contract and routers rather than copied from early endpoint sketches.[^2][^4]

Mobile uses bearer authentication; portal mutations use session cookies and CSRF controls. Request IDs and common API error handling are installed at application composition.[^4]

## Principal record groups

| Domain | Representative records |
|---|---|
| Identity | Login, password hash, verification code, session |
| Directory | Society, plan, vehicle catalogue, service, slot, settings |
| Customer | Customer, vehicle, parking, subscription, onboarding progress |
| Workforce | Crew, weekly hours, exception, pairing, dated society assignment |
| Scheduling | Schedule, placement, unscheduled reason, job/visit relationships |
| Service proof | Checklist snapshots, progress, media, missed-job reason/outcome |
| Billing | Plan/add-on payment, issued invoice, supplier/tax snapshot |
| Customer changes | Skip, pause, cutoff change, coverage extension |
| Support | Complaint, note, visit rating, feedback, check-in and categories |
| Notifications | Device token, event/preference and queued delivery records |

This is a domain map, not an exact table inventory. Requirements describe business entities; implementation models determine physical persistence and relationships.[^5]

## Independent state dimensions

Vehicle active status, subscription status, add-on state and payment state are independent. A customer can own a vehicle with no subscription, while an add-on has its own debt and outcome. Trainee relationships and crew society history also must not be inferred solely from current labels.[^5][^6]

## Migrations and historical data

Schema changes live under `services/api/migrations/versions`. Later revisions cover invoice PDFs, checklist snapshots, alert email, tax/automatic planning, permanent catalogue IDs, society assignments, addresses and booking/catalogue association. The presence of a migration file does not establish that an environment has applied it.[^7]

Historical records preserve relevant checklist/category labels, purchased add-on values and issued tax details. Import paths retain known/unknown legacy fields; they must not fabricate proof or tax values absent from the original record.[^6]

## Time, money and rules

Business cutoffs use IST. User-visible dates use `dd-Mon-yy`; API schemas define wire types. Invoice tax arithmetic uses paise snapshots. The source remains authoritative for rounding and configuration; clients should not duplicate billing calculations from this article.[^1][^6]

## See also

- [Architecture](Architecture.md)
- [Development](Development.md)
- [Site setup](Site_setup.md)

## References

[^1]: [API dependencies](../services/api/pyproject.toml); [architecture draft](../docs/architecture.md).
[^2]: [OpenAPI contract](../packages/api-contract/openapi.json); [exporter](../services/api/scripts/export_openapi.py).
[^3]: [Dart API generator](../apps/mobile/tool/gen_api.dart).
[^4]: [Application setup](../services/api/app/main.py); [cron router](../services/api/app/notifications/cron.py); [web authentication](../services/api/app/webauth/router.py).
[^5]: [Entity audit](../docs/coverage/data-entities.md); [model registration](../services/api/app/models.py).
[^6]: [Owner decisions, 13 October](../docs/reqs/owner-decisions-2026-10-13.md); [test-data plan](../docs/testing/test-data-plan.md).
[^7]: [Migration directory](../services/api/migrations/versions/).

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
