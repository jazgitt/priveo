# Subscriptions

A **subscription** is the recurring-service agreement for one Priveo vehicle. It links a plan, service preferences, lifecycle status and billing dates. A customer with several subscribed vehicles manages and pays for each separately.[^1]

## Plans and preferences

Plans are maintained in Site Setup, with name, monthly and list prices, inclusions and an interior-cleaning flag. Premium Care is the starting plan. A plan's interior flag determines whether the customer must supply a weekly interior-care day. Customers choose a finish-by cutoff in 30-minute steps; this is a scheduling constraint rather than a reserved slot.[^1][^2]

Plans can be deactivated without invalidating subscriptions already using them. When the administrator changes a subscription's plan, the new plan and price take effect at the next renewal rather than rewriting the current period. Customer-initiated plan changes are deferred to V2.[^1][^2]

## Lifecycle

| Status | Meaning |
|---|---|
| Activating | Created, awaiting administrative start/activation |
| Active | Eligible for recurring service generation |
| Paused | Temporarily suspended service under a pause |
| Inactive | No future subscription service or active demand |

The administrator sets the first service date and activates a new subscription regardless of its payment status. Payment receipt and subscription activation are separate decisions. An administrator can make a subscription Inactive with a reason; unpaid plan debt also triggers automatic inactivation under the overdue policy.[^1][^2]

Reactivation returns an Inactive subscription to Activating. The administrator then chooses a new start date, establishing a new billing cycle and Due payment. This is distinct from a routine manual renewal payment.[^2]

## Billing cycle

The default billing cycle is 30 calendar days from the first service date. Renewal falls on the first day after those covered days. For example, a cycle beginning 1 October covers 1–30 October and renews on 31 October before extensions. The displayed “Expires on” date is the last covered day.[^1]

Pauses and operationally skipped exterior-cleaning days extend coverage. Customer skips do not move renewal. Overlapping pause/skip dates must not create duplicate extension credit. A skipped interior job or add-on does not extend the plan.[^1]

The owner made billing cycle and deadline policies configurable on 13 October; fixed values in earlier documents should be read as defaults.[^3]

## Renewal and overdue debt

A plan payment is normally created seven days before renewal and is due on renewal. The customer pays manually by UPI and marks it Initiated; the administrator confirms Received. A plan payment Over due for seven days causes automatic Inactive status by default. Add-on debt does not inactivate a subscription.[^1][^2]

## See also

- [Payments and invoices](Payments_and_invoices.md)
- [Skips and pauses](Skips_and_pauses.md)
- [Add-on services](Add_on_services.md)

## References

[^1]: [Customer requirements](../docs/reqs/customer-app-functional-requirements.md), SUB, PAY and business rules 4, 7, 14, 18 and 26.
[^2]: [Admin requirements](../docs/reqs/admin-functional-requirements.md), ADM-SUB and ADM-SET-01.
[^3]: [Owner decisions, 13 October](../docs/reqs/owner-decisions-2026-10-13.md), decision 7.

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
