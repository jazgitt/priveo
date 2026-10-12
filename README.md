# Priveo Car Concierge

A subscription car-care service for housing societies. A customer pays per vehicle for a daily exterior clean, with interior cleaning on a chosen day, and an optional Deep Spa that is bought separately: as an add-on by a subscriber, or as a standalone service by a customer without a subscription. The crew does each job in the society's parking basement and sends proof of every job: a checklist, photos and a video. A Flutter app on iOS and Android serves customers and crew, with a small set of admin quick actions. Admins do their full work on a React web portal. The role on each login decides what appears.

The repository includes a FastAPI backend, a Flutter customer/crew app and a React admin portal. Development is on `integration/complete-build`; `main` does not yet contain all integrated work. See [the current handoff and remaining implementation plan](docs/codex-handoff-plan.md) for progress, verification and remaining gaps.

Steps 1–3 are implemented locally: recovered email/manager work, customer administration and additional vehicles, and Deep Spa/scheduling integration. Migration head: `0022`. Operations and admin quick actions are the next milestone. These changes have not been committed or deployed.

## Requirements

All three documents are drafts for the MVP (Phase 1). Each requirement has an ID, so items can be added, removed or reprioritised without renumbering the rest.

| Document | Version | Covers |
|---|---|---|
| [`docs/reqs/customer-app-functional-requirements.md`](docs/reqs/customer-app-functional-requirements.md) | v0.5 | Onboarding, plan choice, UPI payment, home, calendar, proof of service, skip and pause, account, subscription, vehicles, complaints, feedback, monthly check-in, notifications |
| [`docs/reqs/admin-functional-requirements.md`](docs/reqs/admin-functional-requirements.md) | v0.4 | Customers and subscriptions, crew, services and slots, capacity, payments and invoices, scheduler with draft and freeze, complaints, feedback, reference data, checklists |
| [`docs/reqs/crew-functional-requirements.md`](docs/reqs/crew-functional-requirements.md) | v0.1 | Login, job cards, performing a job with checklist and proof, could-not-complete, Manager features |

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
