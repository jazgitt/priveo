# Vehicles and societies

**Vehicles and societies** establish the location and ownership context for Priveo service. A customer can own several vehicles, each associated with a society and parking location. Subscriptions and service changes are vehicle-specific.[^1]

## Vehicle information

A vehicle records registration, make, model, variant, category, photo and parking. Make/model/variant choices come from the administrator-maintained catalogue; category is derived from the selected model. Registration is uppercase and validated. Parking records a basement and numeric space number.[^1]

The customer's vehicle photo is required by the onboarding requirements and may be captured or selected from the gallery. It is the identity image shown on Home, distinct from crew service evidence. The crew should identify the car using their job-card vehicle and parking information rather than depending on that photo.[^1][^2]

## Ownership and editing

Customers can change parking and their photo, and manage permitted service preferences. Registration, make, model, variant and category are changed by Priveo. A vehicle's society is fixed once added; separate vehicles belonging to the same customer may use different societies.[^1]

Vehicle activity, subscription status, add-on status and payment status are independent dimensions. An active vehicle may have no subscription or an Inactive subscription. Fixtures also exercise an inactive vehicle with an Active subscription, exposing the need to handle these dimensions separately.[^3]

## Societies

Societies have a name, sector/city and active status. Customers are offered serviced societies. Workforce, working slots, demand and schedules are calculated within society boundaries. A society may be deactivated only after its active subscriptions and active crew have been addressed.[^1][^4]

Dated crew transfers are supported by newer requirements; this does not imply that customers may transfer an existing vehicle to a different society. [Workforce management](Workforce_management.md) describes the separate crew rules.[^4]

## Registration certificates

The customer requirements retain optional RC uploads with JPG, PNG or PDF and a 5 MB limit. The 18 October administrator decision removes RC display, upload and verification from the portal, while explicitly leaving the customer flow unresolved. The wiki therefore does not describe RC verification as a consistent, settled end-to-end capability.[^1][^4]

## Existing-customer imports

The import script supports a trial run by default and a saving mode with `--apply`. Its report identifies spreadsheet rows without printing personal identifiers. Imported customers may have subscriptions or standalone-service vehicles. Real source workbooks remain outside version control in the ignored seed area.[^5]

## See also

- [Subscriptions](Subscriptions.md)
- [Calendar and history](Calendar_and_history.md)
- [Site setup](Site_setup.md)

## References

[^1]: [Customer requirements](../docs/reqs/customer-app-functional-requirements.md), ONB, VEH and business rules 11, 13 and 19.
[^2]: [Crew requirements](../docs/reqs/crew-functional-requirements.md), job-card information and privacy.
[^3]: [Test-data plan](../docs/testing/test-data-plan.md), independent states and C25.
[^4]: [Admin requirements](../docs/reqs/admin-functional-requirements.md), ADM-REF-01–06 and ADM-CRW-22–23.
[^5]: [Import command](../services/api/scripts/import_customers.py); [importer](../services/api/app/customers/importer.py).

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
