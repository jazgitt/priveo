# Glossary

This **glossary** defines Priveo product terms used across the wiki. Domain meanings follow the functional requirements and owner decisions; technical meanings refer to their role in this repository.[^1][^2]

## Product and service terms

| Term | Meaning |
|---|---|
| Add-on | Separately purchased catalogue service for a vehicle |
| Active | Subscription state eligible for recurring service |
| Activating | Subscription awaiting administrator-selected start/activation |
| Billing cycle | Default 30-calendar-day period, adjusted by eligible extensions |
| Cleaning-External | Exterior-cleaning service; default planned duration 20 minutes |
| Cleaning-Internal | Interior-cleaning service; default planned duration 20 minutes |
| Could not complete | Crew action recording a failed job with a reason |
| Covered | Missed work accounted for by the designated subsequent service |
| Cutoff time | Customer's finish-by preference, not a reserved start slot |
| Deep Spa | First separately purchased add-on; default duration 120 minutes |
| Expires on | Last covered subscription day, before the renewal date |
| Inactive | Subscription state without future recurring visits/active demand |
| Job | One service unit performed by assigned crew |
| Missed | Outcome of a job crew could not perform |
| Pause | Range-based suspension with counted extension entitlement |
| Proof | Timed checklist and required uploaded photos/video |
| Renewal date | First day after the covered cycle, accounting for extensions |
| Skip | Individual service removal; billing effect depends on actor/reason |
| Society | Housing community used as the service and capacity boundary |
| Standalone service | Add-on booking for an owned vehicle without a subscription |
| Visit | Service grouping; regular exterior/interior work is distinct from an add-on |

These definitions summarize the requirements; [Subscriptions](Subscriptions.md), [Skips and pauses](Skips_and_pauses.md) and [Operations and recovery](Operations_and_recovery.md) explain their exceptions.[^1]

## Scheduling and workforce

| Term | Meaning |
|---|---|
| Capacity | Available productive crew time subject to society/service constraints |
| Draft | Reviewable schedule before freeze |
| Exception | Sick, Leave or Late-start change to crew availability |
| Freeze | Transition making assignments available to crew under controlled change rules |
| Manager | Crew role with selected society-level operational permissions |
| Member | Crew role contributing full independent capacity |
| Needs scheduling | Queue for work requiring a valid assignment or administrative resolution |
| Trainee | Zero-capacity crew role following a paired Member's work |
| Unfreeze | Controlled reopening for otherwise restricted frozen-schedule changes |
| Working slot | Society/service/day/time window within which work can be planned |

Society moves are dated workforce records; they are different from changing an existing vehicle's society.[^1]

## Payments and governance

| Term | Meaning |
|---|---|
| Due | Payment expected by the specified date |
| Over due | Unpaid record past its due date |
| Initiated | Customer reports payment; receipt awaits administrator confirmation |
| Received | Administrator confirms payment receipt |
| GST snapshot | Recorded tax values retained on an issued invoice |
| Derived | Requirement inferred to support behavior, awaiting owner certainty |
| Owner | Requirement provenance indicating an owner decision |
| Implemented | In the static audit, a matching source path was found |
| Functional Tested | Feature stage supported by mapped functional evidence, subject to review |

Requirement provenance, delivery stage and test coverage are different axes.[^1][^3]

## Technical terms

| Term | Meaning in Priveo |
|---|---|
| Alembic | Database migration tool |
| CSRF | Protection for authenticated portal mutations against forged requests |
| FCM | Selected push-delivery provider |
| IST | India Standard Time, used for business deadlines |
| OpenAPI | Exported API schema used to keep clients aligned |
| OR-Tools | Scheduling optimization library |
| PostHog | Selected usage analytics and optional replay provider |
| Resend | Selected email-delivery provider |
| S3 | Planned private object storage for the AWS launch direction |

Provider selection does not establish live integration or deployment.[^2][^3]

## See also

- [Priveo](Priveo.md)
- [API and data model](API_and_data_model.md)
- [Requirements and roadmap](Requirements_and_roadmap.md)

## References

[^1]: [Customer requirements](../docs/reqs/customer-app-functional-requirements.md); [admin requirements](../docs/reqs/admin-functional-requirements.md); [crew requirements](../docs/reqs/crew-functional-requirements.md).
[^2]: [Technical stack](../docs/tech-stack.md); [owner decisions, 13 October](../docs/reqs/owner-decisions-2026-10-13.md); [owner decisions, 19 October](../docs/reqs/owner-decisions-2026-10-19.md).
[^3]: [Requirements audit](../docs/coverage/requirements-audit.md); [test report, 20 October](../docs/testing/test-report-2026-10-20.md).

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
