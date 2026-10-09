# Priveo Car Concierge

A subscription car-care service for housing societies. A customer pays per vehicle for a daily exterior clean, with interior cleaning and a Deep Spa on top. The crew does each job in the society's parking basement and sends proof of every job: a checklist, photos and a video. One Flutter app on iOS and Android serves customers, crew and admins, and the role on each login decides which screens appear.

This repository currently holds the product requirements and the prototype material they were built from. There is no application code yet.

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
- `Screen1.jpeg` to `screen4.jpeg`: wireframes of the customer flow.
- `Car_Concierge_Vision_Deck.pdf` and the WhatsApp images: context only. They hold no screen behaviour.

### The prototype is partly out of date

The requirements follow the prototype, except where the owner has decided otherwise. Owner decisions win. Do not build these from the prototype or the wireframes:

| Prototype or wireframe shows | Requirements say |
|---|---|
| UPI AutoPay and a "Renew automatically" switch | Every payment is manual: the customer pays by UPI QR or UPI ID and taps "I've paid", then the admin confirms |
| A "Crew rest day" | There is no rest day. Every day is open |
| A 2-hour cleaning slot picker | The customer sets a service cutoff time, in 30-minute steps. The admin assigns the slot |
| One plan, with ₹4,999 in one wireframe | Several plans, chosen by the customer. Premium Care is ₹999 a month, with ₹1,499 struck through |
| Interior cleaning 2 days a week (wireframe) | Interior cleaning once a week, on the customer's interior care day |
| The monthly full spa on the interior day | Deep Spa is separate: 2 hours, once in each 30-day plan, on its own Deep Spa day |
| One crew card with a crew rating | One crew card for each job, and no crew rating. Ratings are general |
| A 9-step wireframe onboarding | The plan is chosen before service preferences. See the customer file, section 1 |
| A "My Vehicles" bottom tab | Bottom tabs are Home, Calendar, Account, Support. Vehicles sit under Account |
| Sample renewal dates that disagree with each other | A billing cycle is 30 calendar days |

## Conventions in the documents

- **Status column:** Defined (the prototype shows it working), Stub, Wireframe, Owner (the owner decided it), Derived (needed to make a stated item work, please check), Open (undecided).
- **IDs:** customer IDs such as `PAY-05`, admin IDs start `ADM-`, crew IDs start `CRW-`. IDs are never renumbered. Retired IDs leave gaps.
- **Dates:** every date in the app is shown as `dd-Mon-yy`, for example `07-Nov-26`.
- **Language:** English only.
- Only functional requirements are listed. Goals, personas and non-functional needs are not.

## Open items

- Starting checklists for Cleaning-Internal and Deep Spa, to be supplied by the owner (`ADM-CHK-07`).
- Deep Spa checks: which date in each plan, whether a skipped Deep Spa is lost, and whether it must finish by the cutoff time (`ONB-24`).
- Two "check" items: the extra plan step in onboarding (`ONB-23`) and a Trainee with no jobs when the paired Member is absent (`CRW-SCH-12`).

The full lists are in section 13 of the admin file, section 11 of the crew file and section 14 of the customer file.
