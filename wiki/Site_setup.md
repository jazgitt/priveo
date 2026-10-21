# Site setup

**Site Setup** is the administrator area for Priveo's reusable catalogue and reference data. Settings hold business configuration shared by the service workflows. Together they determine what customers can buy and how operations execute it.[^1]

## Reference catalogue

| Catalogue | Principal information |
|---|---|
| Societies | Name, location and active status |
| Vehicle catalogue | Make, model, variant and derived category |
| Plans | Permanent plan ID, prices, inclusions and interior flag |
| Services | Service definition and planning duration |
| Working slots | Society, service, weekdays and time windows |
| Add-ons | Permanent add-on ID, description, prices, duration and service |
| Checklists | Ordered service items and proof minimums |
| Reasons/categories | Could-not-complete reasons, feedback tags and check-in categories |

Plan IDs use sequences such as `PLN-0001`; add-on IDs use `ADN-0001`. The identifiers remain permanent while names and catalogue details can change.[^1]

## Services and checklists

Exterior cleaning, interior cleaning and Deep Spa are separate service definitions. Slots belong to a society and service and may vary by weekday. Defaults are editable, so the product should not infer capacity from hard-coded start/end times alone.[^1]

Administrators can add, rename, reorder and deactivate checklist items and set minimum photo/video counts. Crew consume these checklists without editing their definitions. The approved interior and Spa samples each contain five steps and may be changed in the portal.[^1][^2]

## Settings

Support settings hold helpline, WhatsApp and hours. Payment settings hold UPI ID and QR image. Invoice supplier identity is seeded and read-only in MVP. Schedule and billing policy values are configurable, including previously fixed defaults. Automatic planning is a separate opt-in setting with an administrator-selected IST execution time.[^1][^2]

Alert email settings control email routing; they do not remove the mandatory administrator bell/phone-alert requirements. Settings presentation uses separate tabs rather than a single undifferentiated form.[^1]

## Historical preservation

Deactivating a plan or add-on removes it from new offers while preserving existing subscriptions or bookings. Historical checklist wording stays readable. Earlier feedback, rating tags and check-in category results retain their original names after a category rename. Invoice supplier/tax values are snapshots at issuance.[^1][^2]

These are separate forms of historical preservation. An editor should check the relevant transaction's snapshot behavior before assuming every catalogue field is live-linked or immutable.[^3]

## Society deactivation

A society cannot be deactivated while it still has active subscriptions or active crew. The administrator must address those dependencies first. Deactivation then removes the society from customer selection without deleting operational history.[^1]

## See also

- [Admin portal](Admin_portal.md)
- [Scheduling and capacity](Scheduling_and_capacity.md)
- [API and data model](API_and_data_model.md)

## References

[^1]: [Admin requirements](../docs/reqs/admin-functional-requirements.md), ADM-REF, ADM-SET, ADM-SVS, ADM-CHK, ADM-FDB and ADM-ADD.
[^2]: [Owner decisions, 13 October](../docs/reqs/owner-decisions-2026-10-13.md), samples, tax, policies and history.
[^3]: [Directory service](../services/api/app/directory/service.py); [settings registry](../services/api/app/directory/settings_registry.py).

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
