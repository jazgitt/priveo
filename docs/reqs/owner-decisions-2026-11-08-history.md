# Owner decisions: migrated service history (8 Nov 2026)

The owner's position: the service history migrated from the calendar sheet is work that
was really done while the manual process was catching up. It is live and actual, the same as
work done in the app, and it counts everywhere the live history counts. The import is
repeatable, so later catch-up days can be loaded the same way.

| # | Decision | Requirement |
|---|---|---|
| 1 | Migrated days are live history: visits with their jobs, not a separate read-only table. The old table is no longer read; a later migration drops it after the owner checks production. In the customer app they appear as ordinary visits, not tagged "Imported". The admin history still labels them with their source. | ADM-CUS-36, HIST-03 |
| 2 | A plain weekly off writes no visit, the same as a live weekly off. | ADM-CUS-36, HIST-03 |
| 3 | A skipped day keeps the reason written on the sheet (Rain). No reason key is hard-coded: the reason list in the configuration will supply keys later. | ADM-CUS-36 |
| 6 | A migrated visit cannot be rated by the customer. | HIST-03 |
| 4 | A migrated Interior completes its service week and counts like a live Interior. Weeks with no migrated Interior owe nothing extra, so no backlog is created. | SCHR-INT-29 |
| 5 | The import can run again for later days; a day that already has a visit from the app is not written and is reported. | ADM-CUS-36 |

Open: the customer app still offers a rating button on a migrated visit; the server refuses it
(409 visit_not_rateable). Hiding the button needs a flag on the visit detail, a contract change.
