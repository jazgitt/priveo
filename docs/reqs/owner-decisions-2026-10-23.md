# Owner decisions: 23 October 2026

The owner reviewed a requirements document of 43 rows on 23 Oct 2026 and decided the points below. They are recorded as Owner decisions in the three requirements files. Where a row is marked Derived, the owner stated the intent and the detail was filled in to make it workable. Rows marked Draft come from the owner's scenario list and have not been confirmed one by one. Implementation status is in the section at the end.

Terms: "Not Completed" is the job outcome the crew app calls Could not complete, shown to the customer as Missed. "Partially Completed" is a new visit outcome.

1. Customer Skip and Pause stay controlled by the existing feature flag `customer.skip_pause`. No change (D-01, D-02).
2. Only the admin can skip a visit. "Allow Crew Manager to Skip" is the feature flag `crew.manager_skip`, default off.
3. A skipped day does not extend the plan or change that month's cost (B-01). This replaces the earlier rule ADM-CNC-03 / ADM-OPS-03, under which an External skip extended the plan by one day. Pause behaviour is unchanged.
4. Add-on services stay charged separately (B-04). Payment becomes Due if not paid by the scheduled service date, and Over due if the service is completed and payment is not yet received. The code is checked separately.
5. The remark is mandatory for every Not Completed outcome (S-06, C-04, R-07). Reasons stay configured by the admin.
6. No proration of the first billing period or of plan changes (S-10).
7. The admin has a read-only view of the crew serving each vehicle, from the scheduled jobs (D-03).
8. A vehicle's schedule is a Weekly pattern or a Cycle pattern and repeats every cycle (S-02, B-02). Intent Owner, model details Derived.
9. New not-completed reasons (R-02 to R-06): different parking location; keys or customer unavailable; access restricted; customer requested no cleaning; weather or operational issue. The admin can edit all reasons.
10. Crew queue (S-13, C-01 to C-04, B-06): an ordered daily queue, only the current job can be started, the next unlocks on Completed, Partially Completed or Not Completed with reason and remark. No unrestricted crew skip. The admin can reorder or unlock with a mandatory reason, an audit entry and a notification.
11. Partial completion (S-14): Exterior + Interior planned, Interior not done: the visit is Partially Completed, planned and delivered are kept, and the admin or a Manager (flag `crew.manager_reschedule`, default on) decides about rescheduling.
12. Other scenarios added as Draft requirements: S-05, S-07, S-09, S-11, S-12, A-01, A-02, A-04. S-08 is Draft and Open: the prices of Extra interior and Special exterior are not decided.

## Requirement IDs for each decision

Implementation work cites these IDs. A "changed" ID keeps its number and has new wording.

| Decision | New IDs | Changed IDs | Status |
|---|---|---|---|
| 1 Skip and Pause flag | SKIP-10 | none | Owner |
| 2 Only admin skips; Manager skip flag | ADM-OPS-04 | CRW-MGR-02, ADM-CNC-03 | Owner |
| 3 Skip does not extend the plan | none | ADM-OPS-03, ADM-CNC-03, CRW-MGR-02, CRW-CNC-05, SKIP-03; rules: admin 15, customer 25 and 26 | Owner |
| 4 Add-on payment Due and Over due | ADM-PAY-13, ADD-18 | none | Owner |
| 5 Remark mandatory | ADM-CNC-07, CRW-CNC-07 | CRW-CNC-02, crew rule 8 | Owner |
| 6 No proration | ADM-SUB-09 | none | Owner |
| 7 Crew serving a vehicle | ADM-CUS-28 | none | Owner |
| 8 Weekly and Cycle patterns | ADM-SCH-41 | none | Owner and Derived |
| 9 New reasons | ADM-CNC-08 | none | Owner |
| 10 Crew queue | CRW-SCH-14, CRW-SCH-15, CRW-SCH-16, CRW-NOT-06, ADM-SCH-38 | CRW-SVC-11 | Owner (CRW-SCH-14 also Derived) |
| 11 Partial completion | ADM-CNC-09, ADM-CNC-10, CRW-CNC-08, CRW-MGR-07, CAL-11 | CRW-SCH-07 | Owner (ADM-CNC-10 also Derived; CAL-11 Draft) |
| 12 S-05 move one service | ADM-SCH-37 | none | Owner (confirmed 25 Oct 2026) |
| 12 S-07 parking change | ADM-CUS-27, CRW-SCH-17 | none | Owner (confirmed 25 Oct 2026) |
| 12 S-09 bulk reassign | ADM-SCH-39 | none | Owner (confirmed 25 Oct 2026) |
| 12 S-11 plan change from a date | ADM-SUB-08 | none | Owner (confirmed 25 Oct 2026) |
| 12 S-12 bulk missed or cancelled | ADM-SCH-40 | none | Owner (confirmed 25 Oct 2026) |
| 12 A-02 daily dashboard | ADM-ACC-16 | none | Owner (confirmed 25 Oct 2026) |
| 12 A-04 audit | ADM-SET-07 | none | Owner (confirmed 25 Oct 2026) |
| 12 A-01 service-history states | HIST-04, ADM-CUS-29 | none | Owner (confirmed 25 Oct 2026) |
| 12 S-08 add-on catalogue | ADM-ADD-15, ADD-19 | none | Owner (confirmed 25 Oct 2026) |

New feature flags: `crew.manager_skip` (default off), `crew.manager_reschedule` (default on). The flag `customer.skip_pause` already exists.

## Still open

1. ~~Prices of Extra interior and Special exterior.~~ Answered 25 Oct 2026: add-ons are created and priced by the admin in the catalogue.
2. ~~Whether the customer can pick a Weekly or Cycle pattern in the app.~~ Answered 25 Oct 2026: no, admin only. The single interior care day (ONB-18) stays.
3. ~~Plan change from a chosen date: the charge for the days before the renewal.~~ Answered 25 Oct 2026: the admin decides for that customer at that time (no charge, the prorated difference, or an amount). No charge stays the default, so S-10 holds unless the admin chooses otherwise.
4. Whether a missed Interior job of a Partially Completed visit may be rescheduled for any date. (The customer is notified: answered 25 Oct 2026, CAL-11.)
5. ~~Owner confirmation of the Draft rows above.~~ Confirmed 25 Oct 2026.

## Implementation status (24 Oct 2026)

All twelve decisions are built and merged. The owner confirmed the Draft requirement rows on 25 Oct 2026 and they are marked **Owner**. Where the build needed a detail the owner did not give, it was confirmed with the rows.

| Decision | Built in |
|---|---|
| 1 Skip and Pause flag | existing flag `customer.skip_pause` (#61) |
| 2 Only admin skips; Manager skip flag | #70 (`crew.manager_skip`, default off) |
| 3 Skip does not extend the plan | #65 |
| 4 Add-on payment Due and Over due | #65; Over due the moment the service completes (owner, 25 Oct 2026) |
| 5 Remark mandatory; 9 New reasons | #66 |
| 6 No proration | nothing to build; #74 keeps billing as it was |
| 7 Crew serving a vehicle | #72 |
| 8 Weekly and Cycle patterns | #75 (admin only; migration 0039) |
| 10 Crew queue | #69 |
| 11 Partial completion | #66, #70 (`crew.manager_reschedule`, default on) |
| 12 S-05, S-09, S-12 | #70 |
| 12 S-07 parking change | #73 (migration 0037) |
| 12 S-11 plan change from a date | #74 (migration 0038); admin-chosen charge, migration 0040 |
| 12 A-02, A-03, A-04 | #71 |
| 12 A-01 service-history states | derived outcomes #66; the admin history with the filter by state (ADM-CUS-29) in the Vehicles tab, in the pull request that follows #75 |
| 12 S-08 add-on catalogue | #67 (seeded inactive at price 0; question 1) |

