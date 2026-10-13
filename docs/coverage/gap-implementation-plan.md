# Implementation plan for the 79 partial requirement rows

Source: requirements audit of 13 October 2026, integration/complete-build, baseline d5aaad3 plus local invoice/video work. This is a plan, not implementation authorization or a test execution record.

**Progress:** P01-P07 are coded, with P08 audit/policy/bounded refresh and P11 email/escalation sources. Owner decisions of 13 Oct resolve P12 and sample checklist content; standalone Spa, 18% GST snapshots/read-only seller fields, admin mobile checklist view, optional default-disabled timed planning and environment mocks are coded. 45 of the original 79 Partial rows are now addressed: 392 source Implemented, 34 Partial and 0 Open across 426 rows. Literal at-once refresh and full alert phone push remain Partial. Migrations 0024-0028 and all runtime validation remain pending. Preserve the original mapping below; do not execute tests until requested.

The 79 entries are affected requirement rows, not 79 independent features. Shared fixes are organized into 12 packages below; the final mapping assigns every partial row exactly once. The three originally Open rows are outside the 79; owner decisions now resolve them. Sizes describe relative coding scope, not token estimates or promised elapsed time: S = localized, M = several layers, L = lifecycle/integration work.

For each package: confirm the reported source gap against the exact requirement before changing behavior; implement API/client/data changes together; write targeted unit/component regressions; prepare the corresponding functional scenario; update source evidence and the coverage matrices. Keep test execution, builds and database migration execution deferred until the owner asks. Never label unexecuted tests passed or claim measured coverage from test-file presence. Preserve the existing local 5.1/5.3 implementation.

| Package | Rows | Size | Scope | Prerequisite |
|---|---:|---|---|---|
| P01 Rating authorization | 3 | S | Visit existence, customer ownership and Completed-state checks | None |
| P02 Immutable checklist history | 1 | M | Snapshot issued checklist definitions; completed history survives edits | None |
| P03 Billing correctness | 3 | M | Reactivation payment, pause due-date synchronization, plan-change payload | None |
| P04 Crew media integrity | 4 | M | Account-scoped upload queue and strict media boundaries | None |
| P05 Onboarding and payment flow | 7 | L | Step order/persistence, uppercase, totals, amount QR and submitted summary | P03 for payment semantics |
| P06 Customer screen parity | 11 | M | Home/calendar, RC/parking, check-in refresh, feedback overlay and FAQ | P02 for checklist summary data |
| P07 Admin details and lists | 6 | M | Session metadata, pagination, complaint proof/vehicle, imported Spa history | P04 for device/account lifecycle |
| P08 Audit and shared state | 5 | M | Logout-all audit, refresh across clients, admin change notification policy | P03/P07; notification policy before P10 |
| P09 Invoice and proof presentation | 4 | M | GST/settings parity, PDF save/share, inline proof video | P03; owner tax/seller input |
| P10 Real push delivery | 28 | L | FCM/native registration and admin mobile hookup for existing events | P04/P08; Firebase/APNs configuration for live use |
| P11 Admin alerts and timing | 3 | M | Email preference/provider and timely complaint escalation | P10 event/delivery interfaces |
| P12 Standalone Deep Spa | 4 | L | Defined no-subscription booking/payment/scheduling/follow-up | Resolved 13 Oct; P03/P07 |
| Total | 79 | | | |

## P01 — Rating authorization

Put ownership/state checks in the service used by the API, rather than relying on the customer's disabled UI. Reject nonexistent, foreign and unfinished visits; preserve the existing valid-rating/tag/update behavior. Avoid revealing another customer's visit details through errors.

Write regressions for all three rejection cases, valid Completed visits, rating edits, and wrong roles. Functional scenario: a customer can rate their completed visit and cannot submit ratings for other work.

## P02 — Immutable checklist history

Define when a job captures its checklist and persist item identity, label and ordering independently of the mutable catalogue. New catalogue edits affect future work; completed visits keep their original list, names and times. Decide explicitly how already-issued incomplete jobs behave. Add a migration that preserves existing progress; old labels that were already overwritten cannot be reconstructed without historical data, so label the legacy fallback rather than inventing them.

Write rename/add/deactivate/reorder regressions against completed visits, future jobs and existing tick times. Functional scenario: complete a job, edit the catalogue, then reopen the old visit and compare its checklist.

## P03 — Billing correctness

Create exactly one first-cycle Due payment when an Inactive subscription is reactivated and activated with a new first-service date. Keep earlier receipts/history and prevent duplicates on repeated operations. Recalculate renewal and unpaid due dates together on pause/early-end using the shared cycle calculation; protect Received records and assert the specified behavior of Due, Initiated and Over due. Fix portal plan-change payload construction so a newly selected exterior-only plan does not send an incompatible interior day; retain the current plan and price until renewal.

Write lifecycle/idempotency/payment-status regressions and a portal payload test. Functional scenario: reactivate, pause/end early, switch plans, and inspect cycle/payment dates from both admin and customer views.

## P04 — Crew media integrity

Partition SQLite queue rows and files by authenticated owner. Stop/dispose or suspend workers on logout/account change; resume only the current owner's work, preserving recoverable pending uploads without sending them under another login. Specify safe handling of existing unowned queue records. Enforce strictly under 10 MB for photos and 25 MB for videos on capture and API upload/confirmation paths, with clear errors. Preserve the separate RC document limit.

Write account-switch, retry, restart/persistence and closed-job regressions plus just-below/exact/above-limit tests. Prepare native HEIC/capture/offline scenarios; executing them is later validation.

## P05 — Onboarding and payment flow

Implement the prescribed review steps and ensure plan precedes service preferences. Preserve read-only admin-selected society/vehicle/plan fields and multi-vehicle support. Persist allowed draft changes on Continue, restore them after restart and allow backward editing while keeping Home gated by final confirmation. Separate draft persistence from final activation/payment creation so restarting does not create duplicates.

Force registration input uppercase including pasted text. Show a computed total payable today with GST-inclusive wording and per-vehicle amounts. Generate the displayed QR from the backend's amount-bearing UPI URI. Extend the submitted payment DTO/view with vehicle and selected service details.

Write step order/read-only/persistence/restore/multiple-vehicle tests, input-format tests, QR payload tests and payment-summary assertions. Functional scenario: first login and Add Vehicle both reach correct review and payment without losing edits.

## P06 — Customer screen parity

Show make/model/variant on Home; put the named Rate today's clean action on Home and route it through Service Details. Supply completion time/check counts to completed calendar day cards. Invalidate the actual Home check-in provider after submission. Render Verified RC correctly. Use the society's configured parking choices when editing an existing vehicle. Make the feedback tab available on all applicable post-onboarding customer routes. Bundle FAQ Markdown in the app and correct copy that suggests customer self-reactivation.

Write individual widget/navigation/provider assertions, including non-default basement values and submit-to-Home behavior. Functional scenario: navigate Home/calendar/details/account/support and confirm the required content and actions remain consistent.

## P07 — Admin details and lists

Register and expose crew session device/platform/app version metadata; render it in the portal. Add an explicit paging contract/UI for customers and payments with stable ordering, filters and load-more/page behavior. Add vehicle details to complaint summaries, display signed complaint photos and provide an authorized linked-visit/proof view. Map legacy imported standalone Spa records into visible service history without inventing completion status or proof and without duplicating imports; preserve uncertain legacy dates/payment notes honestly.

Write session metadata, over-limit paging/filter, complaint image/visit-access and repeat-import/history regressions. Functional scenario: browse more than one result page and open complete customer/session/complaint/imported-history details.

## P08 — Audit and shared state

Record who/when/target/reason for admin and customer logout-all actions in the same transaction as revocation. Implement a consistent refresh mechanism for already-open customer/admin views after external writes; define and document refresh behavior rather than relying on only local invalidation. Before changing notifications, resolve the interpretation of ADM-CUS-14: plan/preferences edits must be silent, while skip rules explicitly call for skip notifications. Do not blindly suppress every admin-performed operations/skip event; encode the agreed actor/action policy.

Write audit atomicity/session invalidation tests, two-client refresh tests and notification actor-policy assertions. Functional scenario: change state on one client and observe it on the other, then revoke sessions and inspect audit records.

## P09 — Invoice and proof presentation

Build on the existing PDF/viewer code. Add immutable tax breakdown fields/calculation to issued invoices using confirmed tax and seller inputs; preserve legacy-invoice labeling. Make seller fields seed/read-only in MVP in both API and portal. Implement native PDF save/share using the actual PDF bytes, including cancellation/error handling and temporary-file cleanup. Display video playback inline in Service Details while retaining existing retry, signed-URL refresh and lifecycle controls.

Write GST/snapshot/role/ownership/read-only tests, save/share file/content/cancellation tests and inline video lifecycle tests. Prepare native PDF/video scenarios. Do not apply migration 0024 or new migrations until validation is authorized; do not change a migration already deployed elsewhere without checking its deployment history first.

## P10 — Real push delivery

Use the existing event/inbox/preferences infrastructure. Split this large package into P10a backend FCM adapter/error handling, P10b mobile permission/token registration/refresh/logout, P10c admin mobile registration plus foreground/background/cold-start handling, and P10d coverage of each existing event/recipient rule. Respect customer switches and crew role/society scoping; ensure retries do not produce duplicate inbox/event records or resend indefinitely to invalid tokens. Finish missing notification destinations using existing customer destinations where already implemented.

Write mocked provider success/transient/permanent-failure, token rotation/revocation, event fan-out/preference, recipient isolation and route-guard tests. Prepare Android/iOS device scenarios for enabled/disabled preferences and signed-out/cold-start taps. Credentials/OS configuration are needed for live verification, not to write the adapter and mock tests.

## P11 — Admin alerts and timing

Add persisted admin email-alert preference and its portal control; replace LoggingEmailNotifier with configured Resend delivery, preserving inbox alerts when email is off. Run overdue-complaint evaluation often enough to detect the four-hour threshold within a documented short interval, using the same protected cron/domain service and idempotent alert key. Preserve timer authorization and timezone correctness. A scheduler can escalate; it cannot guarantee a human support reply.

Write preference suppression, provider failure/retry, threshold boundary, repeated cron/idempotency and cron authorization regressions. Prepare a functional escalation/alert scenario. Host scheduling/provider configuration and actual delivery are later verification.

## P12 - Standalone Deep Spa (coded after owner decision)

Owner resolved the flow on 13 Oct: admin creates the customer and vehicle without a subscription; customer books/pays/tracks using subscriber Spa rules. API/portal/mobile now create one Add-on payment, schedule independently of payment and expose existing outcome/proof/history. No public signup or synthetic plan is created. Admin can create a standalone booking too. Existing unlinked legacy requests remain honest.

Regressions for creation, payment/idempotency, cutoff/cancel, eligibility, unpaid scheduling and completion are written/unrun. Five-step samples and admin mobile read access are coded; issued history survives edits. See [the owner decisions](../reqs/owner-decisions-2026-10-13.md) and [prepared scenarios](standalone-planning-gst-functional-scenarios.md).

## Completion and validation

Implement one package or subpackage per reviewable change. Update its requirement rows and record tests as written/unrun until execution is requested. Prepare functional scripts alongside each package instead of waiting until the end; repair the stale API smoke and mobile login integration expectations first when preparing those scripts.

After the owner requests testing: execute focused suites and migrations on disposable databases, then relevant broader suites and real provider/device/browser journeys. Close requirement rows only against their exact remaining criteria; configuring a push adapter alone does not prove every event is delivered correctly.

This plan covers the 79 Partial rows. S3 storage, automatic planning host validation (job now coded/default-disabled), offline read/checklist architecture targets, date-format consistency, production infrastructure and release checks remain separate backlog entries in the full audit. They are not silently removed because they were outside this particular 79-row count.

## Exact row-to-package mapping

Generated below from the audit JSON. Each of the 79 Partial rows occurs exactly once; shared packages still require each row's acceptance behavior to be checked.

| Requirement | Package | Gap |
|---|---|---|
| [ONB-25](customer.md#onb-25) | P05 | onboarding-steps |
| [ONB-10](customer.md#onb-10) | P05 | registration-uppercase |
| [ONB-21](customer.md#onb-21) | P05 | onboarding-save |
| [ONB-23](customer.md#onb-23) | P05 | onboarding-steps |
| [PAY-04](customer.md#pay-04) | P05 | onboarding-total |
| [PAY-05](customer.md#pay-05) | P05 | payment-qr |
| [PAY-07](customer.md#pay-07) | P05 | payment-summary |
| [HOME-02](customer.md#home-02) | P06 | home-vehicle-fields |
| [HOME-05](customer.md#home-05) | P06 | home-rate-destination |
| [HOME-08](customer.md#home-08) | P06 | checkin-refresh |
| [CAL-05](customer.md#cal-05) | P06 | calendar-summary |
| [SVC-06](customer.md#svc-06) | P09 | video-inline |
| [SVC-07](customer.md#svc-07) | P01 | rating-validation |
| [SVC-12](customer.md#svc-12) | P01 | rating-validation |
| [SVC-14](customer.md#svc-14) | P01 | rating-validation |
| [SKIP-05](customer.md#skip-05) | P10 | push |
| [SKIP-07](customer.md#skip-07) | P10 | push |
| [NOTIF-01](customer.md#notif-01) | P10 | push |
| [NOTIF-02](customer.md#notif-02) | P10 | push |
| [NOTIF-04](customer.md#notif-04) | P10 | push |
| [NOTIF-05](customer.md#notif-05) | P10 | push |
| [NOTIF-06](customer.md#notif-06) | P10 | push |
| [SUB-12](customer.md#sub-12) | P09 | invoice-save |
| [VEH-03](customer.md#veh-03) | P06 | rc-display |
| [VEH-04](customer.md#veh-04) | P06 | parking-options |
| [ADD-13](customer.md#add-13) | P10 | push |
| [ADD-14](customer.md#add-14) | P12 | standalone-spa |
| [SUP-05](customer.md#sup-05) | P06 | faq-markdown |
| [CMP-04](customer.md#cmp-04) | P10 | push |
| [FDBK-01](customer.md#fdbk-01) | P06 | feedback-overlay |
| [CHK-01](customer.md#chk-01) | P10 | push |
| [CHK-05](customer.md#chk-05) | P10 | push |
| [CHK-08](customer.md#chk-08) | P06 | checkin-refresh |
| [C-07](customer.md#c-07) | P06 | home-rate-destination |
| [ADM-ACC-01](admin.md#adm-acc-01) | P11 | admin-alert-delivery |
| [ADM-ACC-07](admin.md#adm-acc-07) | P10 | admin-mobile-push |
| [ADM-ACC-09](admin.md#adm-acc-09) | P11 | admin-alert-delivery |
| [ADM-ACC-10](admin.md#adm-acc-10) | P08 | cross-client-refresh |
| [ADM-ACC-14](admin.md#adm-acc-14) | P08 | admin-session-audit |
| [ADM-CUS-08](admin.md#adm-cus-08) | P07 | list-paging |
| [ADM-CUS-10](admin.md#adm-cus-10) | P08 | cross-client-refresh |
| [ADM-CUS-14](admin.md#adm-cus-14) | P08 | admin-change-notify |
| [ADM-CUS-15](admin.md#adm-cus-15) | P03 | plan-change-ui |
| [ADM-CUS-16](admin.md#adm-cus-16) | P08 | admin-reset-audit |
| [ADM-SUB-04](admin.md#adm-sub-04) | P03 | reactivation-payment |
| [ADM-CRW-21](admin.md#adm-crw-21) | P07 | crew-session-metadata |
| [ADM-SVS-10](admin.md#adm-svs-10) | P12 | standalone-scheduling |
| [ADM-PAY-01](admin.md#adm-pay-01) | P07 | list-paging |
| [ADM-PAY-06](admin.md#adm-pay-06) | P03 | pause-payment-shift |
| [ADM-PAY-08](admin.md#adm-pay-08) | P09 | gst-invoice |
| [ADM-PAY-11](admin.md#adm-pay-11) | P10 | push |
| [ADM-SCH-21](admin.md#adm-sch-21) | P10 | push |
| [ADM-SCH-24](admin.md#adm-sch-24) | P10 | push |
| [ADM-SCH-27](admin.md#adm-sch-27) | P10 | push |
| [ADM-SCH-28](admin.md#adm-sch-28) | P10 | push |
| [ADM-CMP-01](admin.md#adm-cmp-01) | P07 | complaint-vehicle |
| [ADM-CMP-02](admin.md#adm-cmp-02) | P07 | complaint-proof |
| [ADM-CMP-05](admin.md#adm-cmp-05) | P10 | push |
| [ADM-CMP-08](admin.md#adm-cmp-08) | P11 | complaint-timer |
| [ADM-OPS-01](admin.md#adm-ops-01) | P10 | push |
| [ADM-CNC-04](admin.md#adm-cnc-04) | P10 | push |
| [ADM-REF-05](admin.md#adm-ref-05) | P06 | rc-display |
| [ADM-SET-04](admin.md#adm-set-04) | P09 | gst-invoice |
| [ADM-CHK-05](admin.md#adm-chk-05) | P02 | checklist-history |
| [ADM-ADD-10](admin.md#adm-add-10) | P12 | standalone-spa |
| [ADM-ADD-11](admin.md#adm-add-11) | P07 | imported-spa-history |
| [CRW-ACC-12](crew.md#crw-acc-12) | P04 | queue-isolation |
| [CRW-PRF-04](crew.md#crw-prf-04) | P04 | media-boundary |
| [CRW-SCH-05](crew.md#crw-sch-05) | P12 | standalone-scheduling |
| [CRW-MGR-02](crew.md#crw-mgr-02) | P10 | push |
| [CRW-MGR-03](crew.md#crw-mgr-03) | P10 | push |
| [CRW-SVC-06](crew.md#crw-svc-06) | P04 | media-boundary |
| [CRW-SVC-09](crew.md#crw-svc-09) | P10 | push |
| [CRW-SVC-10](crew.md#crw-svc-10) | P04 | queue-isolation |
| [CRW-CNC-04](crew.md#crw-cnc-04) | P10 | push |
| [CRW-NOT-01](crew.md#crw-not-01) | P10 | push |
| [CRW-NOT-02](crew.md#crw-not-02) | P10 | push |
| [CRW-NOT-05](crew.md#crw-not-05) | P10 | push |
| [CRW-NOT-04](crew.md#crw-not-04) | P10 | push |
