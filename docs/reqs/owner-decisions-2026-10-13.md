# Owner decisions: 13 October 2026

These decisions supersede earlier undecided or fixed-policy wording. They authorize coding and regression sources; tests, builds, migrations and live integration remain deferred.

1. Admin creates customers with their details and vehicles without a subscription. No public self-signup is introduced. A standalone vehicle has no plan or plan payment.
2. Standalone Deep Spa uses the same catalogue price, date/finish-by, UPI/admin confirmation, payment-independent scheduling, change/cancellation, outcomes, proof and history rules as subscriber add-on Spa. A vehicle is required and owned by the customer. Admin can also create a Spa booking for a no-subscription vehicle. Existing unlinked legacy requests retain their known/unknown fields.
3. Use editable five-step samples for Cleaning-Internal and Deep Spa. Admin edits the lists in the web portal and can view them on mobile. Issued checklist history remains unchanged.
4. GST rate is 18%, inclusive in current prices. Environment configuration contains mock supplier identity/GSTIN and tax split values for later replacement offline. CGST_SGST is a mock configuration default, not an assertion about the final jurisdiction. IGST is supported by configuration. Issued tax details are immutable; no breakdown is invented for historical invoices.
5. Build automatic next-period planning now. It is disabled by default. Admin enables/disables it and supplies an IST time. The job creates a reviewable draft using the configured Daily/Weekly/Monthly period, preserves existing schedules, retries failures and alerts admins about errors. Host execution and integration are not enabled/deployed by this coding work.
6. Earlier feedback/rating/check-in results retain their original names and data after category renames. Historical buckets remain separate; no renaming migration is performed.
7. Billing cycle, deadline and unfreeze policies remain configurable through the existing settings. Previously specified values remain defaults. Supplier invoice identity remains seeded/read-only in MVP.
8. Add provider/business placeholder keys to environment configuration. Real keys and values will be supplied offline during later integration, migration and testing. Existing local values must not be overwritten. FCM/APNs/S3/Resend real delivery is not claimed by placeholder configuration.

Internal sample: seats/mats vacuumed; dashboard/panels wiped; interior glass cleaned; door handles/touchpoints cleaned; final inspection.

Spa sample: exterior body cleaned; interior vacuumed; dashboard/panels wiped; glass/wheels cleaned; final inspection.
