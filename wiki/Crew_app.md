# Crew app

The **crew app** is Priveo's mobile experience for assigned service work. Crew use the same installed Flutter application as customers, with role-specific navigation, job cards and a plain light theme.[^1][^2]

## Job visibility

Crew see assigned work after its schedule is frozen. Job cards identify the vehicle, society parking location, service, assigned time, finish-by cutoff and job status. Crew do not receive customer names or mobile numbers. A Manager's broader job visibility remains within their own society.[^1]

Each service is a job. Exterior and interior work on the same day may have separate assignments. A crew member can start a visible job, leave it and return while retaining progress. Completed jobs cannot be changed by crew.[^1]

## Workforce roles

| Role | Capacity and work |
|---|---|
| Member | Counts fully and receives assigned jobs |
| Manager | Counts fully; also has society management permissions |
| Trainee | Adds no independent capacity; follows a paired Member |

A Trainee is paired with exactly one Member in the same society. A Member can have several Trainees. If the paired Member is absent, the Trainee does not receive independent work. Pairing must remain valid when roles or society assignments change.[^1][^3]

## Performing work

The crew member opens a service-specific checklist, checks items as work is done and uploads photographs/video with Before, During or After labels. Completion requires every required checklist item and the service's configured media minimums. Uploads waiting for connectivity remain on the phone; customer-facing completion must wait for successful upload.[^1]

A job that cannot be done is marked Could not complete with a required reason and optional note/photo. It becomes Missed and enters administrative outcome handling. This does not automatically mark every other job of the visit missed.[^1]

## Manager permissions

Managers can view society work, mark another crew member's job could-not-complete or skipped, reassign to a working Member/Manager in the same society, manage attendance exceptions and edit working hours. Manager reassignment is a specific exception to the administrator unfreeze-code rule.[^1]

Managers cannot change passwords, workforce roles or societies, run the scheduler, or freeze/unfreeze schedules. Customer privacy restrictions continue to apply.[^1]

## Profile and notifications

Profile details and working hours are read-only to an ordinary crew member. Crew cannot change their login mobile or password; administrators reset credentials. Assigned-work notification events are mandatory in the product requirements. Crew do not see visit ratings, feedback tags or customer comments.[^1]

## See also

- [Workforce management](Workforce_management.md)
- [Service execution and proof](Service_execution_and_proof.md)
- [Identity and access](Identity_and_access.md)

## References

[^1]: [Crew requirements](../docs/reqs/crew-functional-requirements.md), CRW-SCH, CRW-MGR, CRW-SVC, CRW-CNC, CRW-RAT and CRW-NOT.
[^2]: [Mobile theme](../apps/mobile/lib/core/ui/theme.dart); [build guide](../docs/build-and-release.md), role-specific appearance.
[^3]: [Admin requirements](../docs/reqs/admin-functional-requirements.md), ADM-CRW-14 and ADM-CRW-19–23.

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
