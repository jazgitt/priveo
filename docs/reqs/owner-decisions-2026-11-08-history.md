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

## Sheet status for 4 to 7 Nov 2026 (owner answers, 9 Nov 2026)

| # | Decision | Requirement |
|---|---|---|
| 7 | A Scheduled visit on a day the sheet covers takes the sheet's status. "ext" completes the Exterior; "skipped - <text>" skips it and keeps the text as the reason; "Priveo Missed" is Could not complete. | ADM-CUS-36 |
| 8 | "int,ext" on a visit with no Interior adds a completed Interior. "ext" on a visit with an Interior marks the Interior skipped. | ADM-CUS-36, SCHR-INT-29 |
| 9 | Any reason text is accepted and kept as written. The reason keys in the configuration are the reference list; no text is refused. | ADM-CUS-36 |
| 10 | Updates made from the sheet send no notification. | ADM-CUS-36 |
| 11 | 3 Nov is not changed by this step. | ADM-CUS-36 |
