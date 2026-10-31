# Mani Bond: golden question set, part C

Part C: business requirements, questions 31 to 40. Run and clear on its own with `--set C` (`services/api/tests/mani_eval`). The overview, the review rules and the points to settle are in [`mani-question-set-review.md`](mani-question-set-review.md).

This file is part of the evaluation answer key. It stays out of the search index (`services/api/app/mani/sources.py`, `EXCLUDE_PATHS`). Do not remove that exclusion, or Mani will find its own answers.

## C. Business requirements (source: `docs/reqs/`)

| # | Question | Golden answer | Source | Decision | Notes |
|---|---|---|---|---|---|
| 31 | By when must a customer change a date's schedule, and what happens after? | By 9 PM the previous day, for a skip, un-skip, pause start or end, cutoff-time change or add-on change. After that the controls for that date are disabled and the app shows a message to call the helpline with a "Call support" button. | `SCHED-01`, `SCHED-02` | Keep | |
| 32 | What happens after 5 wrong customer passwords? | Sign-in is blocked for 15 minutes, and the customer can use "Forgot password". | `AUTH-13` | Keep | |
| 33 | How are crew passwords created, handed over and protected from guessing? | Generated automatically as the first 3 letters of the name, 4 random digits and `$` (for example `Raj4821$`). Never sent by SMS or WhatsApp: the admin screen shows the login ID and password once with a Copy button, and the app stores only a hash. After 5 wrong attempts the login is blocked 15 minutes, then 1 hour, then 24 hours. | `CRW-ACC-04`, `CRW-ACC-05`, `CRW-ACC-07` | Keep | |
| 34 | When does a subscription become Inactive for non-payment? | When its plan payment has been Over due for 7 days. An Over due add-on payment does not do this. The admin is alerted and can override it. | `ADM-SUB-03` | Keep | |
| 35 | When does the backend create the plan payment for the next cycle? | 7 days before the renewal date, as Due by the renewal date. It becomes Over due when the due date passes unpaid. If a pause or an operations skip moves the renewal date before the payment is Received, the due date moves with it. | `ADM-PAY-06` | Keep | |
| 36 | When is a schedule frozen, and how does that relate to the customer deadline? | Once, at 8 PM the day before the first day of its period (for a weekly schedule, 8 PM the day before the week starts). Later changes are handled as late changes. The customer deadline is 9 PM, so a skip or pause made after the freeze is removed from the frozen schedule automatically (`ADM-SCH-21`). | `ADM-SCH-25`, `SCHED-01` | Keep | |
| 37 | What happens to crew photos and videos on a poor connection? | They wait on the phone and upload when the connection returns, without being lost. The job is not complete for the customer until everything has uploaded. | `CRW-SVC-10` | Keep | |
| 38 | How does the admin portal keep an admin signed in? | An HttpOnly secure cookie, not tokens in browser storage. Every change request carries CSRF protection. A web session ends after 60 minutes of inactivity. | `ADM-ACC-12` | Keep | |
| 39 | Does skipping a visit extend the plan or change the month's cost, and who can skip? | No. A skipped day does not extend the plan or change that month's cost (the 23-Oct-2026 decision replaces the earlier one-day extension). Only the admin can skip a visit. Letting a Crew Manager skip is the feature flag `crew.manager_skip`, which is off by default. Customer skip and pause stay behind `customer.skip_pause`. | `owner-decisions-2026-10-23.md` items 1 to 3; `SKIP-10` | Keep | |
| 40 | How does a customer pay in the MVP? | Manually by UPI. "Confirm & pay" shows a UPI QR code for the amount and the Priveo UPI ID (copyable). UPI is the only working method: Credit card is shown disabled as "Coming soon", and there is no card, net banking or payment gateway. | `PAY-05` | Keep | |
