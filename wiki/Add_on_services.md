# Add-on services

**Add-on services** are separately purchased services linked to a customer's vehicle. Deep Spa is the first catalogue item and can be sold either to an eligible subscriber or as a standalone service for a customer without a subscription.[^1][^2]

## Catalogue and presentation

An add-on has a permanent ID, name, description, GST-inclusive price, list price, duration, active flag and associated service. The description's first line supplies the customer pitch; later lines become inclusions. Deactivation stops new offers while existing requests continue.[^2]

The 18 October requirements allow multiple active catalogue offerings. With one active item, the customer opens its landing page directly. With several, the customer first chooses an offering. A booking retains the purchased item's name and price, so later catalogue edits should not redefine the transaction.[^1][^2]

## Booking and payment

The customer chooses a vehicle, proposed date and finish-by time. For the subscriber path, Deep Spa requires an Active subscription. For the standalone path, the administrator creates the customer and owned vehicle without a subscription or plan payment. The customer then uses the same booking, UPI payment and service rules. Administrators can also create bookings.[^1][^3]

Scheduling does not depend on payment status in MVP. A customer can therefore have a scheduled booking and a Due payment at the same time. That combination is not, on its own, a data error.[^2]

## Request lifecycle

| State | Interpretation |
|---|---|
| Requested | Booking exists; placement is not confirmed |
| Scheduled | Assigned service placement exists |
| Completed | Service completed with required proof |
| Cancelled | Request withdrawn or cancelled |
| Missed | Crew could not perform the job |

If the requested date cannot fit, the item stays Requested and appears in Needs scheduling. The administrator agrees a new date with the customer; the app must not silently substitute another date.[^1]

## Changes and outcomes

The customer may change or cancel until the default 9 PM deadline the day before service. After freeze, a date/time change becomes a request awaiting Priveo. Administrators are not bound by the customer's deadline.[^1][^2]

The add-on job is separate from the regular plan visit and does not delay that visit's completion. Its proof opens like other service proof. A missed Deep Spa may be retried the next day only or skipped by operations. It does not extend the subscription; any refund or other rebooking is handled by administrators outside the automated MVP flow.[^1]

## See also

- [Scheduling and capacity](Scheduling_and_capacity.md)
- [Payments and invoices](Payments_and_invoices.md)
- [Operations and recovery](Operations_and_recovery.md)

## References

[^1]: [Customer requirements](../docs/reqs/customer-app-functional-requirements.md), ADD-01–17.
[^2]: [Admin requirements](../docs/reqs/admin-functional-requirements.md), ADM-ADD and ADM-SCH-30–31.
[^3]: [Owner decisions, 13 October](../docs/reqs/owner-decisions-2026-10-13.md), decisions 1–2.

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
