# Owner decisions, 04-Nov-26: payment status and cycle

Recorded from the owner's answers in the session of 4 Nov 2026. Requirements: PAY-08, PAY-09, PAY-13 to PAY-19, SUB-09, SUB-10, NOTIF-05 (customer file); ADM-PAY-01 to 03, 06, 07, 12, 14, 15 (admin file).

| # | Decision | Requirement |
|---|---|---|
| 1 | Statuses: Not Due, Due, Due today, Over due, Initiated, Paid. Not Due when more than 7 days remain to the end date; Due for 7 to 1 days; Due today on the end date; Over due after it. Messages say how many days. | PAY-09, PAY-14 |
| 2 | The same rule applies to the first cycle of a new customer. | PAY-14 |
| 3 | Cycle dates never move for early or late payment, pause, skip or credit. | PAY-15 |
| 4 | Customer marks paid (Initiated); admin approves (Paid, "Payment received") or rejects (back to the date rule, "last payment failed"). One Initiated payment per cycle. | PAY-08, PAY-17 |
| 5 | A job at 2:00 IST each day; 02:00 starts the new day. | PAY-19, ADM-PAY-14 |
| 6 | One subscription per vehicle, each with its own cycle. Several vehicles can be paid together. Layout open. | PAY-18 |
| 7 | Reminders at D-7, D-1, the due day, D+1 and D+7. | NOTIF-05 |
| 8 | Admin keeps full control of statuses and offline payments. | ADM-PAY-02, 04 |
| 9 | Sheet-loaded customers: status comes from the payment records the admin enters. | PAY-19, ADM-PAY-15 |
| 10 | Inactive after 7 days Over due stays; the admin is alerted. | ADM-SUB-03, ADM-PAY-14 |
| 11 | A cycle is 30 days with both ends counted (1 Jan to 30 Jan; next cycle starts 31 Jan). | PAY-14, rule 26 |
| 12 | The plan card does not show the cycle end date unless the payment is Over due, then it says the subscription becomes Inactive if not cleared by 7 days after the end date. | SUB-01, ACC-02 |
| 13 | The earlier answer that a pause pushes the end date is cancelled. Pause, skip and credit do not move the cycle. | PAUSE-02, PAUSE-05, PAUSE-06, SKIP-03, rules 4 and 26, ADM rule 15 |
| 14 | Skip and pause dates are limited to the end of the current cycle. | SKIP-09, PAUSE-08 |
| 15 | Not handled now (backlog): refunds B-80, mid-cycle plan change B-81, what happens to a subscription that stays Over due B-82. Service cut-off for overdue is for later. | |
