# Workforce management

**Workforce management** maintains Priveo crew accounts, roles, society assignments, hours, exceptions and Trainee pairing. These records supply the availability used by capacity calculation and scheduling.[^1]

## Onboarding and availability

Administrators create crew with name, unique mobile number, society, role and working hours. Account creation generates a password shown once to the administrator for handover outside the app. Administrators can reset passwords, clear blocks, manage sessions and deactivate crew while preserving history.[^1]

Weekly hours specify working/off status and start/end time for each day. Exceptions cover Sick, Leave and Late start over applicable dates. Managers can edit hours and exceptions for crew in their own society; administrator-only account and role powers remain restricted.[^1][^2]

An exception affecting scheduled jobs releases or reassigns work under the scheduling rules. A crew member's absence must reduce real capacity rather than merely adding an attendance label.[^1]

## Trainees

Trainees contribute zero independent capacity and receive their paired Member's work. Every Trainee has one Member in the same society; a Member can have multiple Trainees. Pairing must be corrected before incompatible role changes. Trainees do not become independent substitutes when their Member is absent.[^1]

## Dated society transfers

Newer requirements allow an administrator to move crew to another society effective today or a future date. Each stay has a start date; it ends the day before the next stay. Earlier associations remain historical facts. Only one move may be pending, and a future move can be cancelled.[^1][^3]

When a move takes effect, open work from that date in the old society returns to Needs scheduling. Started and finished work and earlier dates remain unchanged. The scheduler counts the crew in the new society from the effective date.[^1]

A Trainee moving alone needs a Member in the destination society. Moving a Member carries their paired Trainees on the same date and preserves pairing. Pending-move conflicts must be resolved before the Member move; cancelling that pending Member move cancels the associated Trainee moves.[^1]

The code applies due moves when relevant crew data are opened, before scheduling loads crew and through the daily job. This article follows ADM-CRW-22–23 and the society-move implementation over older “no society transfers” summaries.[^3]

## Capacity boundaries

Members and Managers contribute working capacity; Trainees do not. Capacity is limited by the intersection of crew availability, service slots, society and existing assignments. Deactivation and exceptions must be reflected in demand recovery, with removals from frozen schedules exempt from the unfreeze code.[^1]

## See also

- [Crew app](Crew_app.md)
- [Scheduling and capacity](Scheduling_and_capacity.md)
- [Operations and recovery](Operations_and_recovery.md)

## References

[^1]: [Admin requirements](../docs/reqs/admin-functional-requirements.md), ADM-CRW and ADM-CAP, especially ADM-CRW-22–23 revised 18 October.
[^2]: [Crew requirements](../docs/reqs/crew-functional-requirements.md), CRW-MGR-04–05.
[^3]: [Society-move implementation](../services/api/app/crew/society_moves.py), dated history and due application.

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
