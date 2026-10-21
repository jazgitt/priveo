# Scheduling and capacity

**Scheduling and capacity** turn vehicle-service demand and crew availability into assignments within a society. Priveo uses an OR-Tools-based solver alongside administrative review, manual placement, freezing and a Needs scheduling queue.[^1][^2]

## Inputs and constraints

Demand includes daily exterior work, eligible weekly interior work, add-on requests and allowed missed-job retries. Availability comes from crew hours, attendance exceptions, society assignments and service working slots. Trainees contribute no independent capacity.[^1]

Default planning durations are 20 minutes for exterior and interior cleaning and 120 minutes for Deep Spa. Default cleaning slots are 5–11 AM; Deep Spa can use any time of day. Services and slots are editable, and every day is open in principle.[^1]

The customer supplies a finish-by cutoff in 30-minute steps. A cutoff outside available slots is accepted as a preference; infeasibility is surfaced to administrators rather than rejected in customer onboarding.[^1][^3]

## Planning and review

Administrators select a Daily, Weekly or Monthly period, with Weekly and Sunday-start defaults. A run produces a Draft that can be reviewed, edited and rerun. Manual placements are fixed inputs on rerun rather than disposable suggestions.[^1]

The solver works one society/day at a time. Fixed placements consume capacity. Unfixed work is placed where possible; jobs that fit but miss their finish-by target can be marked late, while unplaceable jobs return a reason. A generated proposal is not automatically proof that every preference was met.[^2]

The portal Board has a Cards editing view and a read-only Timeline. Cards group unassigned work and each crew member's jobs/free slots, with utilization and vehicle/parking details. Dragging places work on a five-minute grid where it fits; an exact-placement dialog is also available. The Timeline presents a compact Gantt-style view, and both views support vehicle/parking search. These are the current ADM-SCH-33 interaction requirements.[^1]

## Freeze and late changes

The default freeze deadline is 8 PM IST on the day before the period starts. Crew visibility follows freeze. Adding or moving work manually in a frozen schedule requires the configured unfreeze-code workflow, followed by review and freeze again.[^1]

Removing work is exempt: customer skips/pauses, operational skips, crew exceptions and deactivation can remove work directly. A Manager's permitted society reassignment is another explicit exception. Eligible late additions and retries can be assigned automatically to available crew; otherwise they enter Needs scheduling.[^1][^4]

The customer's default deadline is later, at 9 PM the preceding day. A permitted skip between freeze and the customer deadline therefore removes frozen work automatically. A cutoff change can instead require an administrative request and replanning.[^1]

## Needs scheduling

The queue identifies work with no viable placement, including capacity gaps, late work and assignments released by workforce changes. Administrators inspect the reason and arrange a valid placement. An add-on that cannot fit stays Requested; its date is changed with customer agreement.[^1]

## Automatic planning

The owner authorized optional next-period draft creation on 13 October. It starts disabled and requires an administrator-selected IST time. The implementation preserves existing schedules, creates reviewable drafts and retries/alerts failures. Host invocation is a deployment concern; enabling a database setting alone does not establish that the job is running.[^5][^6]

Billing period, deadlines and unfreeze policies are configurable; the times and periods above are documented defaults.[^5]

## See also

- [Workforce management](Workforce_management.md)
- [Operations and recovery](Operations_and_recovery.md)
- [Deployment and hosting](Deployment_and_hosting.md)

## References

[^1]: [Admin requirements](../docs/reqs/admin-functional-requirements.md), ADM-SVS, ADM-CAP and ADM-SCH.
[^2]: [Solver](../services/api/app/scheduling/solver.py), placement inputs and outputs.
[^3]: [Customer requirements](../docs/reqs/customer-app-functional-requirements.md), ONB-16–18.
[^4]: [Crew requirements](../docs/reqs/crew-functional-requirements.md), CRW-MGR-03.
[^5]: [Owner decisions, 13 October](../docs/reqs/owner-decisions-2026-10-13.md), decisions 5 and 7.
[^6]: [Automatic planner](../services/api/app/scheduling/automatic.py); [cron jobs](../services/api/app/notifications/cron.py).

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
