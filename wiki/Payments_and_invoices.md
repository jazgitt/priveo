# Payments and invoices

**Payments and invoices** record Priveo's manual collection and administrative receipt process. Plan payments and add-on payments use the same core status vocabulary, but have different due-date and subscription effects.[^1][^2]

## Payment process

The customer sees a UPI QR code, a copyable UPI ID and the amount. Payment is made through an external UPI application. Tapping “I've paid” changes the record to Initiated and alerts administrators. The administrator checks receipt and confirms Received.[^1]

UPI is the only working MVP method. The requirements show credit card as disabled with “Coming soon”; they do not describe a working card gateway or automatic debit. The plan-payment screen is titled “Renew subscription.”[^1]

| Status | Meaning |
|---|---|
| Due | Payment expected by its due date |
| Over due | Unpaid debt past its due date |
| Initiated | Customer reports having paid; confirmation pending |
| Received | Administrator confirms receipt; record closed |

Administrators may set any of the four statuses and can move a payment back to Due or Over due. Changes are audited. Initiated is not proof that money has settled.[^2]

## Timing and debt

By default, a plan payment is generated seven days before renewal and due on renewal. Add-on payment is due on the request day and becomes Over due the next day if unpaid. Plan debt Over due for seven days inactivates the subscription; add-on debt does not.[^1]

Renewal reminders start one week before renewal, recur one day before and then every two days until the payment is Initiated or Received, or the subscription becomes Inactive. The background job must be configured and invoked for automated changes to occur.[^1][^3]

Cancelled unpaid add-ons use voided debt handling rather than a new customer-visible payment status. Already-paid refunds are handled outside the MVP app.[^4]

## GST invoices

An administrator can generate an invoice for a Received payment. Customer billing history exposes issued invoices. The documented invoice number combines `PRV`, two-digit month and year, the final four digits of the customer's contact mobile and four random digits, with a uniqueness check.[^2]

The owner selected 18% GST inclusive in current prices. Supplier identity and tax configuration begin as environment-provided mocks; the default CGST/SGST split is not a jurisdiction ruling. IGST is configurable. Issued supplier and tax values are retained as snapshots, and historical invoices without a recorded split must not receive an invented breakdown.[^5]

This article describes project billing behavior, not independent tax or legal advice. Invoice PDF viewing, saving/sharing and device behavior have separate implementation and validation limits in the handoff.[^6]

## See also

- [Subscriptions](Subscriptions.md)
- [Notifications](Notifications.md)
- [API and data model](API_and_data_model.md)

## References

[^1]: [Customer requirements](../docs/reqs/customer-app-functional-requirements.md), PAY, SUB and business rules 14, 18 and 22.
[^2]: [Admin requirements](../docs/reqs/admin-functional-requirements.md), ADM-PAY-01–12 and ADM-SET-04.
[^3]: [Cron implementation](../services/api/app/notifications/cron.py), payment and reminder jobs.
[^4]: [Test-data plan](../docs/testing/test-data-plan.md), independent payment dimensions; [add-on service](../services/api/app/addons/service.py).
[^5]: [Owner decisions, 13 October](../docs/reqs/owner-decisions-2026-10-13.md), decision 4; [billing service](../services/api/app/billing/service.py).
[^6]: [Implementation handoff](../docs/codex-handoff-plan.md), PDF and release work.

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
