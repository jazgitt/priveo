# Full requirements implementation audit — 2026-10-13

## Result and scope

Reviewed the repository Markdown requirements and current source on `integration/complete-build`, committed baseline `d5aaad3` plus the uncommitted invoice/video, package and owner-decision changes. This is a **static implementation and test-source audit**, not a successful execution report. At the owner's instruction **no unit tests, functional tests, builds, lint, migration checks or coverage measurements were run**.

Packages 1-7 plus P08/P11/P12 and owner-approved changes now address **45 previously Partial rows**, with targeted regressions written/unrun. P05–P07 address 24 more rows. The original [79-row implementation plan](gap-implementation-plan.md) retains its baseline mapping; current pending counts below reflect the changes. Prepared [P01–P04 scenarios](packages-1-4-functional-scenarios.md), [P05–P07 scenarios](packages-5-7-functional-scenarios.md) and the handoff describe validation and legacy-data limits. P08 audit/policy and P11 escalation address four additional rows; 30-second refresh still falls short of at-once propagation and full alert delivery awaits P10 push. P12, checklist samples and GST were specified by the owner and coded. Optional planning is coded/default-disabled; environment mocks are added and historical category names preserved. Prepared [P08/P11 scenarios](packages-8-11-functional-scenarios.md) document those limits. See [the owner decisions](../reqs/owner-decisions-2026-10-13.md) and [prepared scenarios](standalone-planning-gst-functional-scenarios.md). Migrations 0024-0028 are written but unapplied.

The previous coverage tables and grouped overlays are replaced. The review includes **426 ID rows**, **67 numbered business rules**, and **67 data-entity bullets**. Complete source wording, source locations, code links, test evidence and functional-script verdicts are retained in the detailed files. Repeated entity/rule requirements are intentionally counted where they occur; these counts are not unique features or coverage percentages.

| Document | Implemented source path | Partial | Open | Total |
|---|---:|---:|---:|---:|
| [Customer](customer.md) | 182 | 13 | 0 | 195 |
| [Admin](admin.md) | 159 | 13 | 0 | 172 |
| [Crew](crew.md) | 51 | 8 | 0 | 59 |
| Total | 392 | 34 | 0 | 426 |

**Implemented means a corresponding code path was located**, with no known source-level gap recorded for that row. It does not certify every acceptance criterion or runtime behavior. Partial identifies a concrete unmet criterion; Open means required owner input is unresolved. Provider/configuration dependencies can remain on rows whose UI/API logic is implemented. The test column separately identifies targeted assertions versus related-module evidence; **related tests are not a finding that unit coverage is complete**.

Detailed deliverables:

- [Customer matrix](customer.md), [admin matrix](admin.md), [crew matrix](crew.md): every numbered requirement, including the seven customer decision rows.
- [Business rules](business-rules.md): all 31 customer, 25 admin and 11 crew rules.
- [Data entities](data-entities.md): every entity bullet and known missing data fields.
- [Test declaration inventory](test-inventory.md): 753 statically indexed declarations across API, app, app integration and portal. Parametrization, skips and generated/concatenated titles mean this is not a runnable test-case count.
- [Machine-readable evidence](requirements-audit.json): requirement text, verdict, source/code/test locations and remaining limitations.

## Consolidated pending functionality and deviations

This is the full consolidated list of **identified source gaps and completion dependencies**, rather than another summary of the old Step 5 plan. Each entry links to the requirement rows. Implemented-but-unverified dependencies are included so they do not disappear from the remaining work.

| Finding | Affected requirements | What remains | Classification |
|---|---|---|---|
| email-config | [AUTH-03](customer.md#auth-03), [AUTH-05](customer.md#auth-05), [AUTH-16](customer.md#auth-16), [ACC-08](customer.md#acc-08), [ADM-CUS-04](admin.md#adm-cus-04), [ADM-CUS-18](admin.md#adm-cus-18), [ADM-CUS-19](admin.md#adm-cus-19) | Customer Resend adapter/templates and fail-closed production paths exist. Verified sender/domain and actual delivery remain unverified; tests use fake/mocked delivery. | Configuration/verification or recorded limitation |
| legal-content | [AUTH-04](customer.md#auth-04) | Consent timestamp and tappable Terms/Privacy links are present; public legal URLs/content are configuration placeholders and not verified. | Configuration/verification or recorded limitation |
| business-config | [AUTH-15](customer.md#auth-15), [SUP-02](customer.md#sup-02), [SUP-03](customer.md#sup-03), [ADM-SET-02](admin.md#adm-set-02), [ADM-SET-03](admin.md#adm-set-03) | Functional controls exist, but repository defaults use placeholder UPI/QR/contact values. Live configured values are not established by this source audit. Pre-login support-contact reads environment settings, not the admin database settings. | Configuration/verification or recorded limitation |
| video-inline | [SVC-06](customer.md#svc-06) | New in-app video screen has duration, seeking/playback/retry; the Service Details tile pushes a separate screen instead of literal play-in-place. New player tests are written but not run. | Code/UI gap |
| push | [SKIP-05](customer.md#skip-05), [SKIP-07](customer.md#skip-07), [NOTIF-01](customer.md#notif-01), [NOTIF-02](customer.md#notif-02), [NOTIF-04](customer.md#notif-04), [NOTIF-05](customer.md#notif-05), [NOTIF-06](customer.md#notif-06), [ADD-13](customer.md#add-13), [CMP-04](customer.md#cmp-04), [CHK-01](customer.md#chk-01), [CHK-05](customer.md#chk-05), [ADM-PAY-11](admin.md#adm-pay-11), [ADM-SCH-21](admin.md#adm-sch-21), [ADM-SCH-24](admin.md#adm-sch-24), [ADM-SCH-27](admin.md#adm-sch-27), [ADM-SCH-28](admin.md#adm-sch-28), [ADM-CMP-05](admin.md#adm-cmp-05), [ADM-OPS-01](admin.md#adm-ops-01), [ADM-CNC-04](admin.md#adm-cnc-04), [CRW-MGR-02](crew.md#crw-mgr-02), [CRW-MGR-03](crew.md#crw-mgr-03), [CRW-SVC-09](crew.md#crw-svc-09), [CRW-CNC-04](crew.md#crw-cnc-04), [CRW-NOT-01](crew.md#crw-not-01), [CRW-NOT-02](crew.md#crw-not-02), [CRW-NOT-05](crew.md#crw-not-05), [CRW-NOT-04](crew.md#crw-not-04) | Backend events/inbox/preference or crew fan-out hooks exist, but sender is LoggingPushSender and default mobile NoPushTokenProvider returns null. Firebase/OS permission/token refresh/logout/foreground-background handling and device delivery remain missing. Related tests mock delivery. | Code/UI gap |
| invoice-save | [SUB-12](customer.md#sub-12) | PDF view code exists, but file save/native share is missing; current copy/email actions send text. New PDF tests are written/unrun; migration 0024 is unapplied. GST breakdown is separately tracked in entity/technical findings. | Code/UI gap |
| admin-alert-delivery | [ADM-ACC-01](admin.md#adm-acc-01), [ADM-ACC-09](admin.md#adm-acc-09) | P11 adds own-admin persisted alert email address/switch, portal control, durable recipient queue and configured Resend delivery with bounded retries/stable provider key. Email opt-out preserves inbox/push; missing key leaves pending delivery. Real phone push still awaits P10. Migration 0027 and API/portal regressions written/unrun; actual host/provider delivery unverified. | Code/UI gap |
| admin-mobile-push | [ADM-ACC-07](admin.md#adm-acc-07) | Specified payment/schedule/operations/customer/crew/complaint/report quick screens exist; actual phone push is absent and admin home does not watch pushRegistrationProvider. Unit/widget tests cover a subset of actions. | Code/UI gap |
| cross-client-refresh | [ADM-ACC-10](admin.md#adm-acc-10), [ADM-CUS-10](admin.md#adm-cus-10) | P08 adds foreground 30-second refresh plus app resume/browser focus/reconnect refresh; active customer/admin reads observe last committed writes, and draft fields are retained. Literal at-once propagation still needs a real-time transport. Refresh/API/component regressions written/unrun. | Code/UI gap |
| complaint-actor-display | [ADM-CMP-07](admin.md#adm-cmp-07) | Database updates store author_login_id/time, but UpdateOut/portal thread display only generic Admin/Customer, not which admin made each change. Backend recording is present; visible actor identity is incomplete. | Configuration/verification or recorded limitation |

Additional cross-cutting items outside a single numbered row:

1. **5.4 notification destinations:** customer inbox already routes visits, payment, complaint and check-in. Crew inbox drops reference ID and taps only mark read. Admin alert navigation handles only a subset of reference types. Finish the missing destinations, authorization checks and signed-out/cold-start replay; do not rebuild the destinations already present.
2. **5.6 production storage:** `app/media/store.py` returns only `LocalObjectStore`. The protocol/signing/upload-confirmation and ownership tests exist; no S3 implementation is selected. Add configured private S3 storage, verified byte/content checks, expired/incomplete-upload cleanup and production URL handling. Do not count a local store as a deployed S3 integration.
3. **5.8 automatic next-period planning:** coded, disabled by default. Admin must supply an IST time to enable it. Minute-check cron creates the next configured Daily/Weekly/Monthly draft for active societies, preserves existing schedules, tracks target/lease/retries and raises error alerts. Migration 0028, concurrent-worker checks, host cadence and regressions are unrun. No deployment was performed; manual planning remains available.
4. **Date/time consistency:** shared formatters exist, but portal audit/session timestamps still use browser locale; crew timestamps use device local time. Finish the all-role dd-Mon-yy/IST policy.
5. **Proof photo expiry:** video retry refreshes signed proof URLs; the photo viewer has no equivalent automatic refresh while open. Native HEIC/photo rendering still needs device validation. Step 5.3 is coded, not proven on devices; the player is a separate screen rather than literal inline playback.
6. **Option rename history:** owner explicitly keeps earlier names/data and separate historical buckets. No rename migration is desired; preservation regression source is written/unrun.
7. **Live business values:** UPI/QR, support contacts, legal document URLs, seller identity/GSTIN and sender domain are development defaults or unverified. This audit does not claim that external accounts/credentials do not exist. Pre-login support values come from environment settings while signed-in support comes from directory settings; reconcile the two sources.
8. **MVP rule configuration:** owner authorized configurable cycle/deadline/unfreeze policies; prescribed values remain defaults. First onboarding cycle now uses the configured length. The unfreeze code remains plaintext, contrary to the stack's hashed-config target; this technical hardening remains pending.

The existing operations skip extensions, next-day retries, media closed-job guard, manager attendance/hours, vehicle job-card photos, admin reference CRUD and removal of crew rating access are present. Old matrix statements saying these are wholly unbuilt are superseded.

## Unit and component coverage assessment

There are existing service/solver tests, API TestClient scenarios with test databases, Flutter widget/repository tests with fakes, and portal React Testing Library tests with mocked HTTP. These are meaningful source evidence but are different levels of testing. API router/database scenarios are component/in-process functional tests; calling every one a pure unit test would be inaccurate.

The per-row test-evidence distribution is:

| Evidence classification | Requirement rows |
|---|---:|
| Partial | 1 |
| Present (mocked) | 35 |
| Present (related) | 6 |
| Related tests present | 278 |
| Targeted regression present | 51 |
| Written; not run | 55 |

Rows with only related tests **do not have established complete acceptance coverage**. This report explicitly leaves that unproven instead of upgrading them to “Unit Tested >95%”. The declaration inventory enables inspection of actual assertion sources. New invoice PDF/video and P01-P07 tests are written but unexecuted; migrations `0024` through `0028` remain unapplied.

Packages 1–7 now have written API/component regressions for rating authorization, checklist snapshots, billing corrections, queue isolation/media boundaries, onboarding drafts/order/totals, uppercase paste, payment QR/context, Verified RC/configured parking, calendar timing/counts, check-in refresh, global feedback, FAQ parsing, crew metadata, customer/payment paging, complaint proof and imported history. These are unexecuted. P08/P11 add audit rollback, actor/count, last-committed reads, refresh lifecycle, email suppression/retry/address changes and escalation boundary/rollback sources, also unrun. Remaining regression gaps include native queue restart/SQLite upgrade on devices; notification destination authorization/cold start; all-role date formatting; save/share PDF lifecycle. Written scenarios do not establish runtime acceptance or measured coverage.

Historical Step 4 results in the handoff: 409 SQLite API tests, 129 affected-module PostgreSQL tests, 68 portal tests, 191 mobile tests with 11 skips. These are recorded prior results, **not a new run and not evidence for the latest invoice/video code**. No current line/branch coverage measurement or above-95% result is available in this audit. Feature-status stages are not promoted.

## Functional scripts: what is ready

| Existing artifact | Scope | Source readiness and remaining work |
|---|---|---|
| `services/api/scripts/smoke_test.py` | Health, bad-password path, three role logins/homes | **Stale, not ready unchanged:** requests `/v1/crew/home`, which has been removed. Requires credentials/seeded records. Repair this before using it as a deploy gate. It does not cover MVP business journeys. |
| `apps/mobile/integration_test/logins_test.dart` | Role sign-in/home/sign-out on device/emulator | **Stale, not ready unchanged:** expects old `Hello,` greeting while current customer greeting changes by time. Seed/onboarding assumptions need alignment. It does not cover operations/payment/proof journeys. |
| `apps/mobile/test/live_api_test.dart` | Narrow live API auth/home/privacy | **Conditional:** skips without live defines; needs the intended seeded API. It is not a full device functional suite. |
| API test scenarios under `services/api/tests/` | Scheduling, lifecycle, billing, support, role boundaries against a test DB | **Present as in-process scripts:** isolated database/fakes, not live-provider/device journeys. New PDF dependency/migration checks remain pending; tests not run in this audit. |
| Flutter widget and portal RTL files | Screen interactions with injected/mocked repositories/HTTP | **Present as component scripts:** do not establish native permissions, media decoding, real QR payments, real email/push or browser end-to-end behavior. |
| `apps/mobile/tool/push_apk.ps1` | Builds current checkout's dev APK, copies to phone Downloads | **Build/distribution helper only:** contains no functional assertions. It does not constitute functional test coverage. |
| Playwright/Cypress admin browser suite | Main portal journeys | **No suite located.** Vitest/RTL tests exist; Playwright remains a stack/testing target. |

Complete cross-role functional scripts still needed:

1. Admin creates customer → real email first-sign-in/reset → customer review/pay → admin receipt/activation → second vehicle in another society.
2. Crew roles/hours/exceptions/pairing → manual plan/rerun/swap/suggestion → freeze → crew/customer assignment → skip/pause/cutoff and late work after freeze.
3. Crew checklist + compressed photos/video → loss of connection/restart/account switch → upload confirmation → completion → owned customer proof/history/rating.
4. Missed Exterior/Internal/Spa → valid next-day retry or operations skip → no duplicate jobs/extensions → correct customer calendar and unpaid payment dates.
5. Renewal/Over due/seven-day inactivity/reactivation → check-in/reminder preferences → deployed authorized cron → correct notifications, routing and no duplicates.
6. Complaint with vehicle/visit/photos → admin status/note/actor → four-hour escalation → customer notification; feedback/tag/category edits and consent/history.
7. Received payment → issued invoice snapshot/GST → PDF view/save/share; expired URLs, failure/retry, roles/ownership and native behavior.
8. Portal cookie/CSRF/inactivity/logout-all; phone admin inactivity; all-role privacy, formatting and large-list behavior.

These are **missing functional coverage**, not claims that the underlying functionality is all missing. Functional execution stays deferred until requested.

## Technical Markdown targets and actual code

Architecture is marked draft; stack choices are decided. Later documented owner decisions take precedence: customer four tabs and no crew ratings override the old architecture shells; the 10-Oct fixed per-role appearance documented in build-and-release supersedes earlier theme-switch proposals. V2 items (public signup, gateways/AutoPay, crew self-password/leave/swaps, two-factor auth and society transfers) are not counted as MVP missing code.

| Source target | Code/source evidence | Assessment | Unit/functional evidence |
|---|---|---|---|
| Flutter/Riverpod/go_router/Dio/secure tokens | `apps/mobile/pubspec.yaml`, `lib/core/auth`, `lib/core/routing` | Present; no native security-storage verification this audit | Auth/widget tests; live/device journey incomplete |
| FastAPI/Pydantic/SQLAlchemy/Alembic/Postgres/Argon2/OR-Tools | API project/config, identity and scheduling modules; migrations | Present; migrations 0024-0028 not checked/applied | Service/router/solver tests; historical Postgres results only |
| Three audience OpenAPI schemas (architecture decision 2) | `packages/api-contract/openapi.json`, export generator, generated Dart API | One combined schema instead of three; role guards still present | Role/schema tests are not audience-contract separation |
| In-process background solver (architecture decision 3) | `app/scheduling/router.py::run` calls service directly | Synchronous request execution; no durable job/progress/retry worker. Separate from automatic planning gap | Solver/scenario tests exist; load/recovery functional script missing |
| Drift cached reads/checklists and offline writes | `pubspec.yaml`, crew queue/checklist repositories | sqflite media queue exists; Drift/cached last-good reads/local checklist and missed writes are absent | Queue fakes exist; offline shift/device journey missing |
| Workmanager background uploads, resume-on-open | Mobile queue and pubspec | Resume-on-open/connectivity exists; no Workmanager worker while app closed | Native background/restart assertions missing |
| Camera/image_picker/video compression/HEIC | capture modules, API media validation | Capture/compression exists; exact bounds/native HEIC need work/validation | Upload/router/widget tests; native decoding pending |
| Firebase FCM/APNs/local foreground notifications | LoggingPushSender/NoPushTokenProvider; no Firebase deps | Missing real adapter/SDK/native integration | Mocked event tests only |
| Resend email and retry | `platform/email.py`, identity/account/customer flows, support notifier | Customer code/welcome and P11 admin alert Resend adapters are coded; persisted recipient preferences and bounded durable retries are written/unrun. Live delivery/bounces/provider behavior unverified | Mocked delivery/failure tests; live script missing |
| Private S3/CloudFront, upload cleanup, image derivatives | `media/store.py` only local store | S3 integration/retention cleanup/resize derivatives absent | Local signed URL and ownership tests only |
| ReportLab invoice/PDF in S3 | `billing/pdf.py`, issued snapshots, PDF endpoints | ReportLab code written; no S3-stored PDF or GST breakdown/save/share | New tests unrun; native/browser journey missing |
| Web React/Vite/Query/router, generated typed client | `apps/web/package.json`, API client and app/pages | Core present; verify generated schema use separately from handwritten feature DTOs | Vitest/RTL; no browser E2E |
| TanStack Table, React Hook Form/Zod, Tailwind/shadcn, dnd-kit, Recharts | Web package dependencies, custom tables/forms/Board/components | Decided libraries are absent; custom controls provide parts of behavior. Record a stack deviation; paging/functionality gaps remain separately | Component tests do not prove library/design parity |
| Bell polling, shared admin services, cookie/CSRF/session expiry | AlertBell, webauth/platform/websession, shared routes | Present; email/push/cross-client immediate refresh/audit gaps above | Auth/CSRF/component tests; live session journey missing |
| Force-update/minimum version gate | Public config endpoint, mobile startup/router | Version config exists; enforced app update gate not located | Native old-version scenario missing |
| Crashlytics/Sentry/CloudWatch structured alarms | Mobile dependencies, API middleware, deployment workflow | Request IDs present; crash SDK/production alarms not established | No crash/alarm functional verification |
| Brand tokens/fonts/native splash/icon | Token generators, theme, bundled fonts/assets | Present with documented fixed role themes/temporary raster mark. Master vectors await owner | Golden source exists; visual/130% text-scale/contrast pass pending |
| `/v1` versioning/contract checks/standard errors | API routers/errors/export and CI | Present; detailed backward compatibility and all-route errors require later validation | Contract/auth/validation tests; not rerun |
| Single module service boundaries/event coupling | Cross-module SQL reads in billing/scheduling/customer_reads | Architecture boundary ideal is not fully followed; functional implementation exists | Refactor target, not automatically an MVP feature omission |
| Environments/AWS ECS/RDS/Secrets/S3/EventBridge/portal hosting | `api-deploy.yml`, Vercel config; documented AWS switch; no infra provisioning tree | Workflow branch exists, not proof of production/staging resources. Dev Vercel/Neon is an explicit later choice | External setup/live configuration not audited |
| Android CI/signing/Play pipeline | `.github/workflows/mobile-*.yml`, fastlane/android | Pipeline source exists; repo secrets/accounts/release delivery not established. PR native-build coverage target still needs review | Login integration stale; no release executed |
| iOS/macOS signing/TestFlight pipeline | iOS scaffold, workflow inventory | iOS scaffold exists; no iOS release workflow located | Native iOS/permissions/media/push testing pending |
| >95% rule coverage, goldens, load/security/restore checks | CI/tests and historical reports | Tests exist; no current >95% measurement, full E2E, realistic scheduler load, accessibility or restore evidence | Validation/release work pending; not executed here |

## Production network/access checkpoints

N1–N14 are **release targets**, not certifications inferable from application source. No cloud credentials, secrets, DNS, current CI runs or deployed configuration were inspected. The development exception (Vercel/Neon over public TLS) is documented; it must not be called a compliant private production deployment.

| Checkpoint | Static evidence / current limitation | Verdict |
|---|---|---|
| [N1](../../docs/architecture.md#71-network-and-access-checkpoints) | Deploy workflow can use AWS, but no live load balancer/DNS/TLS/public endpoint inventory was checked. | Deployment verification pending |
| [N2](../../docs/architecture.md#71-network-and-access-checkpoints) | No verified private ECS subnet/security-group configuration in this audit. | Deployment verification pending |
| [N3](../../docs/architecture.md#71-network-and-access-checkpoints) | No verified private RDS public flag/security-group configuration; dev Neon is documented exception. | Deployment verification pending |
| [N4](../../docs/architecture.md#71-network-and-access-checkpoints) | Database TLS/configuration does not prove encryption/backups or a successful restore. | Deployment verification pending |
| [N5](../../docs/architecture.md#71-network-and-access-checkpoints) | Dev deploy directly runs migration/seed from CI. Production ECS one-off migration/break-glass policy is unverified. | Deployment verification pending |
| [N6](../../docs/architecture.md#71-network-and-access-checkpoints) | AWS deploy workflow uses role assumption/OIDC path; actual IAM trust/least privilege unverified. | Partial code; deployment unverified |
| [N7](../../docs/architecture.md#71-network-and-access-checkpoints) | Application reads environment secrets; deployed Secrets Manager injection and log/image/repository secret audit unverified. No secret values read. | Partial code; deployment unverified |
| [N8](../../docs/architecture.md#71-network-and-access-checkpoints) | NAT/S3 gateway endpoint/egress security configuration unverified. | Deployment verification pending |
| [N9](../../docs/architecture.md#71-network-and-access-checkpoints) | Public authorized cron routes and Vercel entries exist. No private EventBridge task configuration verified; automatic planner coded/default-disabled; host deployment unverified. | Partial code; deployment unverified |
| [N10](../../docs/architecture.md#71-network-and-access-checkpoints) | Local signed-media ownership/expiry checks exist; private S3 bucket/public-access policy and exact byte bounds incomplete/unverified. | Partial code; deployment unverified |
| [N11](../../docs/architecture.md#71-network-and-access-checkpoints) | API lockout/code limits exist; WAF deployment/rate rules unverified. | Partial code; deployment unverified |
| [N12](../../docs/architecture.md#71-network-and-access-checkpoints) | Environment flags and Android dev/prod exist; actual separate prod/staging databases/buckets/secrets unverified. | Deployment verification pending |
| [N13](../../docs/architecture.md#71-network-and-access-checkpoints) | RequestIdMiddleware exists; CloudWatch infrastructure/security-change alarms and delivery unverified. | Deployment verification pending |
| [N14](../../docs/architecture.md#71-network-and-access-checkpoints) | Swagger/ReDoc disabled in create_app, but default /openapi.json is still enabled. Production needs disabling/protection; mock code is production-gated in identity configuration. | Partial code; deployment unverified |

## Document reconciliation and audit manifest

Latest functional specs take precedence over historical component/build snapshots. Requirements are not renumbered. Owner decisions of 13 Oct resolve standalone/checklist content, GST mocks, configurable policies and optional planning; the decision record supersedes older undecided wording. `docs/system-component-diagram.md` describes Phase 0 and falsely suggests the current portal/database/scheduler are absent; treat it as historical. The overnight/build/release documents retain historical milestone descriptions. README previously advertised older requirement versions; versions are corrected with this audit. The handoff's Step 5 list remains useful sequencing, but is no longer a complete list of missing functionality.

All repository-authored Markdown files found outside dependency/build/cache directories were included in document review. The line counts below are source inventory counts, not a claim that every prose line is an independent feature. Requirement tables/rules/entities are transcribed into audit rows; technical/delivery decisions are assessed above; instructions/how-to/historical claims and V2 exclusions are reconciled rather than silently counted as MVP gaps. The iOS launch-image README is template customization guidance, not a product requirement. New generated audit artifacts are deliverables, not new input requirements.

| Markdown input | Lines | Treatment |
|---|---:|---|
| [README.md:1](../../README.md#L1) | 60 | Historical/status/instruction review; not independent feature counts |
| [CLAUDE.md:1](../../CLAUDE.md#L1) | 59 | Historical/status/instruction review; not independent feature counts |
| [docs/architecture.md:1](../../docs/architecture.md#L1) | 368 | Technical/release target reconciliation |
| [docs/build-plan.md:1](../../docs/build-plan.md#L1) | 208 | Technical/release target reconciliation |
| [docs/build-and-release.md:1](../../docs/build-and-release.md#L1) | 126 | Technical/release target reconciliation |
| [docs/overnight-build-report.md:1](../../docs/overnight-build-report.md#L1) | 80 | Historical/status/instruction review; not independent feature counts |
| [docs/system-component-diagram.md:1](../../docs/system-component-diagram.md#L1) | 75 | Historical/status/instruction review; not independent feature counts |
| [docs/tech-stack.md:1](../../docs/tech-stack.md#L1) | 226 | Technical/release target reconciliation |
| [docs/reqs/customer-app-functional-requirements.md:1](../../docs/reqs/customer-app-functional-requirements.md#L1) | 567 | Complete per-ID/rule/entity audit |
| [docs/reqs/admin-functional-requirements.md:1](../../docs/reqs/admin-functional-requirements.md#L1) | 487 | Complete per-ID/rule/entity audit |
| [docs/reqs/crew-functional-requirements.md:1](../../docs/reqs/crew-functional-requirements.md#L1) | 227 | Complete per-ID/rule/entity audit |
| [docs/reqs/owner-decisions-2026-10-13.md:1](../../docs/reqs/owner-decisions-2026-10-13.md#L1) | 16 | Historical/status/instruction review; not independent feature counts |
| [docs/coverage/customer.md:1](../../docs/coverage/customer.md#L1) | 205 | Historical coverage fully replaced by current per-row matrix |
| [docs/coverage/admin.md:1](../../docs/coverage/admin.md#L1) | 182 | Historical coverage fully replaced by current per-row matrix |
| [docs/coverage/crew.md:1](../../docs/coverage/crew.md#L1) | 69 | Historical coverage fully replaced by current per-row matrix |
| [apps/mobile/README.md:1](../../apps/mobile/README.md#L1) | 17 | Historical/status/instruction review; not independent feature counts |
| [apps/web/README.md:1](../../apps/web/README.md#L1) | 30 | Historical/status/instruction review; not independent feature counts |
| [apps/mobile/ios/Runner/Assets.xcassets/LaunchImage.imageset/README.md:1](../../apps/mobile/ios/Runner/Assets.xcassets/LaunchImage.imageset/README.md#L1) | 5 | Historical/status/instruction review; not independent feature counts |

## Implementation ordering after this audit

1. Packages 1–7 code and targeted tests are now written; validation remains deferred. P08/P11 coding is recorded with remaining real-time/push dependencies. P12 and the owner-approved job/samples/GST changes are coded; remaining targets are PDF save/share, inline video, real-time refresh, P10 push, S3 and date/security/release work.
2. Continue remaining packages for audit/shared-state parity, invoice save/share and tax/settings, notifications/email/planning, decision-dependent standalone Spa and shared date formatting. Validate P05–P07 UI and legacy-data scenarios when testing is authorized.
3. Finish Step 5 integrations: PDF save/share and tax/settings parity, push/navigation, S3, admin alert email preference/delivery, business configuration, automatic planning and host timers. Owner checklist/standalone decisions are resolved; live configuration is deferred.
4. Add targeted regressions for the listed acceptance gaps and repair/extend live/device/browser scripts. Tests can be written under the user's coding-only instruction, but execution still requires the user's later request.
5. When requested, validate the latest changes/migrations in isolated databases and run component/unit suites, then real provider/device/browser journeys. Complete production infrastructure/checkpoints, load/restore/accessibility/signing/store release work before release.

The report does not claim that passing a unit suite proves live services, or that an unverified deployment is absent. The original audit changed documentation only; the subsequent owner-authorized packages 1–7 changed application code and regression sources, without executing validation.
