# Priveo Car Concierge

A subscription car-care service for housing societies. A customer pays per vehicle for a daily exterior clean, with interior cleaning on a chosen day, and an optional Deep Spa that is bought separately: as an add-on by a subscriber, or as a standalone service by a customer without a subscription. The crew does each job in the society's parking basement and sends proof of every job: a checklist, photos and a video. A Flutter app on iOS and Android serves customers and crew, with a small set of admin quick actions. Admins do their full work on a React web portal. The role on each login decides what appears.

The repository includes a FastAPI backend, a Flutter customer/crew app and a React admin portal. Development is on `integration/complete-build`; `main` does not yet contain all integrated work. See `docs/coverage/unit-test-coverage.md` for verification evidence and `docs/reqs/owner-decisions-2026-10-23.md` for the current work.

For synthetic manual testing, see [the scenario catalogue, full/partial seed commands and E2E plan](docs/testing/test-data-plan.md). The fixture tool supports a dedicated local database with one Admin login and independently resettable Customer/Crew scenarios.

Implementation packages through the owner-approved standalone Spa, GST, checklist and optional-planning work are committed and pushed as `2c3ba73` on `integration/complete-build`. The owner has now authorized tests and coverage improvements. Fresh coverage exceeds 90% of executable lines for Customer, Crew, Admin Mobile, Admin Web and shared code; see [the measured report](docs/coverage/unit-test-coverage.md). Coverage improvements are uncommitted. Migrations 0024-0028 remain unapplied to the application database; deployment and live integration are pending.

## Requirements

Packages P01-P07, P08/P11 sources and owner-approved P12/GST/checklist/optional-planning changes are implemented and committed in `2c3ba73`; the fresh automated suites now pass as recorded in the measured coverage report. Automatic planning is disabled by default and requires an admin-selected IST time. Environment mocks preserve existing local values; real integration is deferred. The [audit](docs/coverage/requirements-audit.md) has 392 Implemented source rows, 34 Partial and 0 Open. Migrations 0024-0028 are unapplied. Immediate real-time refresh, PDF save/share/inline proof, P10 push, S3 and date/security/release work remain pending.

The [full source audit](docs/coverage/requirements-audit.md) replaces the old coverage summaries: 426 requirement rows, 67 business rules and 67 entity bullets, with separate implementation, test-source and functional-script findings. Remaining work includes correctness and UI gaps beyond the Step 5 integrations. No tests were run for this audit.

All three documents are drafts for the MVP (Phase 1). Each requirement has an ID, so items can be added, removed or reprioritised without renumbering the rest.

| Document | Version | Covers |
|---|---|---|
| [`docs/reqs/customer-app-functional-requirements.md`](docs/reqs/customer-app-functional-requirements.md) | v0.11 | Onboarding, plan choice, UPI payment, home, calendar, proof of service, skip and pause, account, subscription, vehicles, complaints, feedback, monthly check-in, notifications |
| [`docs/reqs/admin-functional-requirements.md`](docs/reqs/admin-functional-requirements.md) | v0.9 | Customers and subscriptions, crew, services and slots, capacity, payments and invoices, scheduler with draft and freeze, complaints, feedback, reference data, checklists |
| [`docs/reqs/crew-functional-requirements.md`](docs/reqs/crew-functional-requirements.md) | v0.5 | Login, job cards, performing a job with checklist and proof, could-not-complete, Manager features |

Start with the customer document, then admin, then crew. Each file ends with its open questions and its V2 list.

## Prototype material

In [`docs/prototype/`](docs/prototype/):

- `Priveo Customer App Prototype.html`: interactive customer prototype. Open it in a browser.
- `Car_Concierge_Vision_Deck.pdf` and the WhatsApp images: context only. They hold no screen behaviour.

### The prototype is partly out of date

The requirements follow the prototype, except where the owner has decided otherwise. Owner decisions win. Do not build these from the prototype:

| Prototype shows | Requirements say |
|---|---|
| UPI AutoPay and a "Renew automatically" switch | Every payment is manual: the customer pays by UPI QR or UPI ID and taps "I've paid", then the admin confirms |
| A "Crew rest day" | There is no rest day. Every day is open |
| A 2-hour cleaning slot picker | The customer sets a service cutoff time, in 30-minute steps. The admin assigns the slot |
| The monthly full spa on the interior day | Deep Spa is 2 hours and bought separately: as an add-on by a subscriber, who proposes one date and a finish-by time, or as a standalone service by a customer without a subscription |
| One crew card with a crew rating | One crew card for each job, and no crew rating. Ratings are general |
| Sign-in by mobile number and SMS OTP, then the customer fills in their own details | Sign-in by email: a code on first sign-in, then a password. Only customers the admin created can sign in, and the onboarding steps open pre-filled for review |
| A "My Vehicles" bottom tab | Bottom tabs are Home, Calendar, Account, Support. Vehicles sit under Account |
| Sample renewal dates that disagree with each other | A billing cycle is 30 calendar days |

## Conventions in the documents

- **Status column:** Defined (the prototype shows it working), Stub, Owner (the owner decided it), Derived (needed to make a stated item work, please check), Open (undecided).
- **IDs:** customer IDs such as `PAY-05`, admin IDs start `ADM-`, crew IDs start `CRW-`. IDs are never renumbered. Retired IDs leave gaps.
- **Dates:** every date in the app is shown as `dd-Mon-yy`, for example `07-Nov-26`.
- **Language:** English only.
- Only functional requirements are listed. Goals, personas and non-functional needs are not.

## Open items

- Starting checklists for Cleaning-Internal and Deep Spa, to be supplied by the owner (`ADM-CHK-07`).
- How a customer without a subscription requests, pays for and follows a standalone Deep Spa (`ADD-15`, `ADM-ADD-12`).

The full lists are in section 13 of the admin file, section 11 of the crew file and section 14 of the customer file.
