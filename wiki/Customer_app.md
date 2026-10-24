# Customer app

The **customer app** is the customer-facing role of Priveo's Flutter application for Android and iOS. It presents the customer's selected vehicle, subscription, service evidence, payments and support. Its top-level navigation comprises Home, Calendar, Account and Support.[^1]

## Entry and onboarding

MVP access begins with an administrator-created customer account. On first sign-in, an emailed six-digit code precedes password creation and a review of prefilled details. An unregistered email receives a contact-support message rather than a public signup journey.[^1]

The review covers personal details, society, vehicle, parking, plan, service preferences and confirmation. Customers can correct fields they normally control, including names, contact mobile, parking and vehicle photo. Society, established vehicle identity and the administrator-selected plan are restricted. Home becomes available after onboarding confirmation.[^1]

An administrator may create a customer and vehicle without a subscription for standalone service. That vehicle should not acquire an artificial plan or plan payment merely to enable booking.[^2]

## Home and navigation

Home is scoped to the selected vehicle. Its combined vehicle card includes the customer's vehicle image, registration, make/model/variant, subscription status, plan name, society, parking and the last covered date. Home does not display the plan price. A vehicle without a subscription is identified accordingly.[^1]

The next-service area remains relevant until the crew close that service, even after its expected time. Completion opens access to proof. Monthly check-in and payment-related actions link to their own workflows. Switching vehicles changes the context of calendar, history and schedule changes.[^1]

Top-level tabs reset their navigation stack when switched. Detail screens use a back action. The feedback control is a movable icon at the screen edge after onboarding; it is absent from crew and administrator experiences.[^1]

## Account and service management

Account contains profile, settings, vehicles, subscription and billing access. Vehicle identity changes go through Priveo; supported self-service edits include parking, photo and service preferences. A different vehicle can belong to a different society, but a vehicle's established society is fixed.[^1]

Customers inspect service through [Calendar and history](Calendar_and_history.md), buy [add-on services](Add_on_services.md), mark payments paid and submit complaints or feedback. A subscription change and an add-on purchase are separate transactions with different effects.[^1]

## Refresh and presentation rules

Current requirements avoid timed refresh and specify refresh on return after five minutes or more away. Previously opened bottom tabs stay loaded, and refresh retains existing content until replacement data arrives. Immediate updates across clients remain a separate implementation concern. Dates use `dd-Mon-yy`; the app's MVP language is English. The usage-data notice and settings switch are documented separately in [Analytics and privacy](Analytics_and_privacy.md).[^1][^3]

## See also

- [Identity and access](Identity_and_access.md)
- [Vehicles and societies](Vehicles_and_societies.md)
- [Support and feedback](Support_and_feedback.md)

## References

[^1]: [Customer requirements](../docs/reqs/customer-app-functional-requirements.md), AUTH, ONB, HOME, NAV, VEH, SET and account sections.
[^2]: [Owner decisions, 13 October](../docs/reqs/owner-decisions-2026-10-13.md), decisions 1–2.
[^3]: [Test report, 20 October](../docs/testing/test-report-2026-10-20.md), refresh and integration gaps.

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
