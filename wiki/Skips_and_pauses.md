# Skips and pauses

**Skips and pauses** let customers suspend recurring vehicle service for individual dates or a date range. They share deadline and coverage rules but have different effects on the renewal date.[^1]

## Comparison

| Change | Service effect | Renewal effect |
|---|---|---|
| Customer skip | Removes the chosen day's service | No extension |
| Customer pause | Suspends service across the approved range | Extends coverage for counted paused days |
| Operational exterior skip | Operations removes exterior work | One day of extension for the affected day |
| Operational internal/add-on skip | Removes that job | No subscription extension |

These differences are part of the business rules. An operational skip must not be recorded as a customer skip merely because both remove a job.[^1][^2]

## Deadlines and covered dates

The default customer deadline is 9 PM India Standard Time on the preceding day. It applies to skip, un-skip, pause changes and relevant schedule changes. After it, customers are directed to the helpline. Administrators acting on behalf of a customer are exempt from that customer deadline.[^1][^2]

The 18 October wording limits customer skips and pauses to dates covered by the current plan. MVP specifies no general minimum or maximum pause length, but that does not allow selection outside the currently covered dates. Policy values are configurable following the 13 October decision.[^1][^3]

## Pause accounting

Counted paused visits move the renewal date forward; ending a pause early recalculates the extension. A skipped date within a pause is counted once as a paused day. Duplicate or overlapping changes must not inflate entitlement.[^1]

Interior service skipped or paused on its chosen weekday is lost for that week and is not separately made up. This differs from a missed internal job, where operations can arrange a next-day retry.[^1]

## Frozen schedules

A permitted customer skip or pause after freeze removes the affected work automatically and alerts administrators. Removing work does not require the administrative unfreeze code. Cutoff changes after freeze follow a request workflow because they may require moving work.[^2]

Un-skip and pause-ending actions can introduce demand again. Their scheduling treatment must respect remaining capacity and frozen-schedule rules; restoring entitlement is not a guarantee of a particular crew slot.[^2][^4]

## See also

- [Subscriptions](Subscriptions.md)
- [Scheduling and capacity](Scheduling_and_capacity.md)
- [Operations and recovery](Operations_and_recovery.md)

## References

[^1]: [Customer requirements](../docs/reqs/customer-app-functional-requirements.md), SKIP, PAUSE, SCHED and business rules 2–4, 25–27.
[^2]: [Admin requirements](../docs/reqs/admin-functional-requirements.md), ADM-CUS-09–11 and ADM-SCH-21–29.
[^3]: [Owner decisions, 13 October](../docs/reqs/owner-decisions-2026-10-13.md), configurable policies.
[^4]: [Changes service](../services/api/app/changes/service.py); [scheduling service](../services/api/app/scheduling/service.py).

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
