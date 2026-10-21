# Notifications

**Notifications** communicate Priveo service outcomes, support changes, payment reminders and operational exceptions. Product requirements distinguish customer preferences from mandatory crew and administrator alerts.[^1][^2][^3]

## Customer events

Customer events cover service completed, service skipped, complaint updates, renewal reminders and monthly check-in. Each event is on by default and can be disabled by the customer. Completed add-ons reuse the service-completed event instead of introducing a separate notification type.[^1]

Renewal reminders follow the billing cadence. Monthly check-in is due four days before renewal by default, while its Home card remains visible independently of notification preference. Complaint status changes and notes generate complaint-update events.[^1]

## Crew events

Crew are notified of newly frozen/changed work, removed work, permitted Manager reassignment and automatic post-freeze assignment. These events cannot be disabled within the crew product. Reassignment also affects paired Trainees as specified.[^2]

## Administrator alerts

Alerts include customer changes after freeze, cutoff requests, changed/cancelled add-ons, missed jobs, automatic assignment, Needs scheduling, automatic inactivation, Initiated payment and new/overdue complaints. Administrator bell and phone-push events are mandatory in the requirements; email channels are configurable.[^3]

Complaint alert email includes a brief operational summary and a portal link rather than attaching photographs. The implementation has queued email delivery and retry handling.[^3][^4]

## Delivery architecture

The repository separates notification records/events, adapters, device-token registration, push sending and support email delivery. FCM is the selected push provider and Resend the email provider. A stored event or passing adapter test is not proof of delivery through those providers on a real device.[^5][^6]

The implementation handoff records remaining push, navigation and live-integration work. The 20 October report excludes live-provider and device tests. Requirements saying “sends push” should therefore be understood as intended behavior unless linked deployment evidence establishes delivery.[^6]

## Scheduled jobs

The current internal cron router registers eight jobs: crew-society-moves, automatic-planning, freeze-due, payments-generate, payments-overdue, renewal-reminders, checkin-notify and complaints-overdue. Calls require `CRON_SECRET`; missing configuration yields a disabled response. The router accepts GET and POST.[^7]

The development schedule configuration and cron comments include host-specific timing compromises. The eight-job list and actual host configuration should be checked together before claiming punctual freeze, reminders or escalation. Automatic planning still respects its disabled-by-default setting.[^7]

## See also

- [Payments and invoices](Payments_and_invoices.md)
- [Support and feedback](Support_and_feedback.md)
- [Deployment and hosting](Deployment_and_hosting.md)

## References

[^1]: [Customer requirements](../docs/reqs/customer-app-functional-requirements.md), NOTIF and business rules 15, 22–23.
[^2]: [Crew requirements](../docs/reqs/crew-functional-requirements.md), CRW-NOT.
[^3]: [Admin requirements](../docs/reqs/admin-functional-requirements.md), ADM-ACC-09, ADM-SCH-24 and ADM-CMP-08.
[^4]: [Support email delivery](../services/api/app/support/email_delivery.py).
[^5]: [Notification events](../services/api/app/notifications/events.py); [push adapter](../services/api/app/notifications/push.py).
[^6]: [Implementation handoff](../docs/codex-handoff-plan.md); [test report, 20 October](../docs/testing/test-report-2026-10-20.md).
[^7]: [Cron implementation](../services/api/app/notifications/cron.py); [development host configuration](../services/api/vercel.json).

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
