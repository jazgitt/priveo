# Calendar and history

**Calendar and history** are the customer views of planned and past service for the selected vehicle. They connect scheduling outcomes to job details, proof, ratings and complaints.[^1]

## Calendar scope

The calendar is scoped to a vehicle and its billing cycle. It shows the plan duration and service-day markers, including separately scheduled add-ons. Current requirements grey days without subscription coverage; a different service state should not be treated as absence of a subscription.[^1]

The customer chooses a finish-by cutoff rather than a cleaning slot. Once assigned, the calendar and day detail show crew and assigned timing. A customer can inspect multiple jobs on a day, each with its own crew card; a regular exterior-plus-interior visit need not be performed by one person.[^1][^2]

## Service states

Scheduled, Completed, Skipped and Missed describe different outcomes. A customer skip, a pause and an operational skip must preserve their different billing and extension consequences. A missed job is not equivalent to a completed job with no proof.[^1]

For missed service, customer wording records the outcome, such as “Rescheduled on” or “Covered on” with a date. Current service-detail requirements expose the crew's reason, free-text note and optional photo. A missed external job may be covered by the next regular exterior job; internal and Spa retry rules are narrower.[^1][^3]

## Proof and detail

Service Details contains timed checklist progress, photos, video and crew information for the relevant service. Media stages are Before, During and After. Ratings are attached to the visit and are general; they are not crew-specific performance scores.[^1]

The service-details entry also supports reporting an issue with that visit preselected. Customers can select another eligible visit or no linked visit when creating a complaint.[^1]

## History and imports

Requirements place imported and newly created service history in one newest-first list. Every row opens details. An imported row should preserve whatever evidence and fields were actually imported; missing historical data must not be presented as newly recorded proof.[^1][^4]

The backend has dedicated customer-read projections for calendar and service presentation. These combine underlying subscription, schedule, change and outcome data into customer-facing representations rather than requiring clients to reconstruct business rules.[^5]

## See also

- [Service execution and proof](Service_execution_and_proof.md)
- [Skips and pauses](Skips_and_pauses.md)
- [Operations and recovery](Operations_and_recovery.md)

## References

[^1]: [Customer requirements](../docs/reqs/customer-app-functional-requirements.md), CAL, SVC, ISS-02 and history requirements.
[^2]: [Admin requirements](../docs/reqs/admin-functional-requirements.md), scheduling assignments.
[^3]: [Crew requirements](../docs/reqs/crew-functional-requirements.md), CRW-CNC-05–06.
[^4]: [Customer importer](../services/api/app/customers/importer.py); [owner decisions, 13 October](../docs/reqs/owner-decisions-2026-10-13.md), legacy unknown fields.
[^5]: [Calendar projection](../services/api/app/customer_reads/calendar_view.py).

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
