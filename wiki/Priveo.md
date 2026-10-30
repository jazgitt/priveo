# Priveo

**Priveo Car Concierge** is a car-care service for housing societies. Its product combines recurring vehicle cleaning, separately booked add-on services, photographic service evidence and administrative scheduling. Customers and crew use a Flutter mobile application; administrators use a React web portal and selected mobile quick actions.[^1]

| Product characteristic | Description |
|---|---|
| Operating unit | Housing society and vehicle |
| Customer platforms | Android and iOS application |
| Administration | React web portal; limited mobile actions |
| Backend | FastAPI modular application |
| MVP language | English |
| Payment model | Manual UPI payment with administrative confirmation |

## Service model

A subscription belongs to a vehicle. The starting plan describes daily exterior cleaning and weekly interior cleaning on the customer's chosen day, alongside listed care inclusions. Exterior and interior cleaning are separate jobs, with default planning durations of 20 minutes each. Deep Spa is purchased separately and has a default duration of two hours. Catalogue settings determine the actual plans and add-ons offered; prototype prices are not an authoritative live price list.[^1][^2]

Work takes place in the society's parking area. Customers specify parking and a finish-by cutoff time; administrators assign the actual service slot. Every weekday is eligible for service: the product has no fixed weekly rest day.[^1]

## Audiences

Customers manage their own vehicles, service preferences, payments, proof and support requests. Crew perform assigned jobs and record checklist progress and media. Crew Managers also manage selected work and attendance within their society. Administrators maintain customers, workforce, schedules, catalogues, payments and support records.[^2][^3]

The same mobile login screen determines the role from the account. A crew Manager is a workforce role within the crew experience; it does not confer full administrator access.[^3]

## Product lifecycle

1. An administrator creates a customer and vehicle, optionally with a subscription.
2. The customer verifies their email, sets a password and confirms prefilled onboarding details.
3. For a subscription, the administrator selects the first service date and activates it. For a standalone add-on, the customer can book without creating a subscription.
4. The administrator plans service using crew capacity, reviews a draft and freezes the schedule.
5. Crew execute jobs and upload evidence. Customers inspect completed service or follow missed-job outcomes.
6. Payments, renewal, feedback and complaints continue independently through their respective workflows.[^1][^2][^4]

## Boundaries and maturity

MVP payments use UPI QR or UPI ID. A customer's “I've paid” action requests confirmation; it does not verify settlement. Public self-signup, automatic payment collection and in-app refunds are outside the described MVP.[^1]

Repository implementation is broader than the old Phase 0 diagrams suggest. Nevertheless, the latest recorded tests do not establish production readiness, real-device behavior or live email, push and media integration. The proposed [Mani Bond](Mani_Bond.md) assistant has its own specification and solution plan and should be read separately from the implemented car-care workflows.[^5][^6]

## See also

- [Customer app](Customer_app.md)
- [Scheduling and capacity](Scheduling_and_capacity.md)
- [Architecture](Architecture.md)
- [Requirements and roadmap](Requirements_and_roadmap.md)

## References

[^1]: [Customer requirements](../docs/reqs/customer-app-functional-requirements.md), PAY, ONB, business rules and deferred features.
[^2]: [Admin requirements](../docs/reqs/admin-functional-requirements.md), services, plans, scheduling and access.
[^3]: [Crew requirements](../docs/reqs/crew-functional-requirements.md), CRW-ACC and CRW-MGR.
[^4]: [Owner decisions, 13 October](../docs/reqs/owner-decisions-2026-10-13.md), standalone service and configurable policies.
[^5]: [Test report, 20 October](../docs/testing/test-report-2026-10-20.md).
[^6]: [Mani Bond architecture](../docs/agent/agent-architecure.md), recommended solution and rollout.

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
