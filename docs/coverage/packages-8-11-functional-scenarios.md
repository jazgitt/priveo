# P08 and P11: prepared functional scenarios

Code and regression sources are written; no tests, builds or migrations executed. Migration 0027 follows unapplied 0024-0026. P12 was subsequently specified and coded; see [the updated scenarios](standalone-planning-gst-functional-scenarios.md).

## P08 audit, refresh and notification policy

Sign into two admin devices and one customer device. Revoke the customer's sessions from admin. Confirm every customer token is rejected at its next server contact and one shared audit records the admin, customer target, timestamp, reason and count. Logout-all for the admin must record the same fields and revoke only that admin's sessions. An audit insert failure must roll back revocation, rather than leaving an unaudited successful sign-out.

Keep Home, account/vehicle/subscription, calendar/payment/support/history and admin views open while editing the same record from another client. Active reads refresh within 30 seconds in the foreground; browser focus/reconnection and native resume refresh immediately. Background polling does not issue reads. Local form drafts remain editable. Last committed writes appear on reread. The current implementation is bounded polling, not literal at-once propagation; those two rows remain Partial. Manually paged native history refreshes its first page. Existing read/error states still apply.

Change a plan or default cutoff/interior preference through admin: no customer notification. Explicit skips and operations skips retain their separately required notification, respecting customer notification preferences; admin skips identify Priveo. Confirm these policy cases independently.

Sources: API test_gap_session_audit.py, test_customer_administration.py, notifications/test_events.py; native customer/read_refresh_test.dart; portal AlertEmailSettings.test.tsx. Device lifecycle, two-client UI and transaction fault journeys remain unexecuted.

## P11 email preference, delivery and escalation

In portal Settings, configure My alert emails for the signed-in admin. Save an address and enable/disable email; invalid/empty enabled addresses fail. A customer/crew cannot use the endpoint or edit another admin. Background refresh preserves a typed draft. The preference remains after reload.

Raise a configured admin alert. The inbox remains available independently of push/email. With email disabled, no recipient delivery is queued; disabling or changing the address before a pending send stops that old delivery. It is not redirected or replayed on re-enable. With RESEND_API_KEY and EMAIL_FROM configured, delivery uses Resend and a stable provider idempotency key. Missing credentials leave pending work without consuming attempts. A provider failure schedules increasing retries, stops after five failed attempts and preserves the inbox. A failed push must not suppress email. Actual delivery and provider keys must be verified on an authorized environment later.

Create a Raised complaint and cross exactly four hours. Before the boundary no overdue alert is raised; at/after the boundary one alert and its email deliveries are saved with the escalation marker in the same transaction. Repeated cron calls do not duplicate it. Rollback on insert failure leaves the marker unset, so a later run can retry. Resolved complaints are excluded.

Host configuration temporarily calls /v1/internal/cron/complaints-overdue daily at 21:00 IST (15:30 UTC) with CRON_SECRET for Vercel Hobby compatibility. Overdue escalation and email retries can wait until the daily run; the original frequent escalation cadence remains deferred. Hobby invocation timing can vary within the scheduled hour. Verify missing/wrong secret rejection, actual invocation times and detection on the first run after the boundary. This timer does not implement automatic day/week schedule planning. No host deployment was performed.

Sources: support/test_alert_email_delivery.py, existing support/test_support.py and notifications cron tests; portal AlertEmailSettings.test.tsx. Migration, PostgreSQL row locking, real email/provider/device delivery and deployed cadence are unverified. Real FCM/admin phone push remains P10, so full three-channel alert rows remain Partial.
