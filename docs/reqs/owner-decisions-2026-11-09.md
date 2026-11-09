# Owner decisions: cutoff-driven scheduling (9 Nov 2026)

The owner's decisions on the scheduler's cutoff rules, recorded before the code change.
The rows changed in `scheduler-requirements.md` (v0.10), `admin-functional-requirements.md`
(ADM-SCH-07) and `customer-app-functional-requirements.md` (ONB-16).

| # | Decision | Requirement |
|---|---|---|
| 1 | A protected job is any job of the service Cleaning-External (the Exterior daily clean). Interior and Deep Spa are not protected. There is no priority flag: protection comes from the service only. | SCHR-CUT-09 |
| 2 | Normal placement is in ascending order of the cutoff time, so an early cutoff is done early. This applies to Exterior and Interior jobs. | SCHR-CUT-10 |
| 3 | The home zone stays the normal rule. A protected job may be rescued by a cleaner of another zone when it would otherwise be late, after the normal rules are applied. Example: cleaner C1 of zone z1 does a z3 job before its own z1 job when the z3 job has an earlier cutoff and the z3 cleaner cannot place it on time. | SCHR-ZONE-12 |
| 4 | Order of the rules: the normal rules first (placed, zone, cutoff order, break, fifo and the rest), then the cross-zone rescue, and only then a protected job placed late. A protected job is placed late rather than left unplaced, and is unplaced only when no capacity is left. An emergency exception is out of scope. | SCHR-CUT-09, SCHR-HIER-09 |
| 5 | An Interior that cannot be placed on the day goes to Unscheduled. It is not made late on a weekday. On a weekend the Interior keeps the soft cutoff. This is reported to the owner, not changed (open, see below). | SCHR-CUT-11, SCHR-WKE-01 |
| 6 | The weekday rule is unchanged, including the weekday hard cutoff for Interiors. The only change to weekday behaviour is decision 4 for protected jobs. | SCHR-CUT-01 to SCHR-CUT-04 |
| 7 | (Q3, 9 Nov 2026, later) Interior jobs are ordered by the oldest service week first, then by the cutoff time, both ascending. The fifo week order ranks above the cutoff order. Exteriors keep the cutoff order. | SCHR-INT-12, SCHR-CUT-10, SCHR-HIER-09 |
| 8 | (Answer B, 9 Nov 2026, later) All Exteriors are planned on time first (Pass A). Protected lateness and the rescue override the home zone. A protected Exterior that cannot be on time is placed late on weekdays and on weekends, or left unassigned on a frozen day. | SCHR-CUT-09, SCHR-ZONE-12 |

## How the decisions were built (Derived)

- Decisions 7 and 8 replace the earlier reading of the cutoff order as a single key across all jobs: the order is now fifo (week), then the cutoff, then protected lateness and the home zone are as before. Inside one week the ledger-age tie-break of SCHR-INT-12 still decides which Interior is placed when they compete; the cutoff orders the start.

- The objective order is placed, protected lateness, home zone, cutoff order, cleaner break, fifo, other lateness, usable early capacity, earlier start (SCHR-HIER-09). Decision 4 is read as: a rescue overrides the home zone only to save a protected job from lateness. Every other choice keeps the home zone first.
- Decision 4 is applied on every strict day, so a protected Exterior is also placed late on a strict weekend day when the site's weekend cutoff is set to not flexible.
- The cutoff order is kept across cleaners, not only within one cleaner.
- The stored default objective order changes on existing sites through migration 0055 (only where the stored value is still the old default). The branch is not merged, so no site holds the new default yet.

## Open for the owner

1. Weekend Interiors keep the soft weekend cutoff (decision 5). Kept as it is, and reported here.

Answered in this record: the strict-weekend reading (decision 8, placed late on weekends too) and the Pass B order (decision 7, fifo ranks above the cutoff).
