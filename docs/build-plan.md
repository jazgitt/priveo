# Priveo Build Plan

**Status:** v0.4, 10 Oct 2026. Phase 0a is built except delivery through Play: steps 1, 2, 5 to 9 and 12 are done, and steps 3 and 4 run on Vercel in place of AWS for `dev`. Step 10 (Play internal testing) is written as a workflow and waits on the owner's Play Console account. Step 11 (iOS) is not started and waits on the Apple Developer account. The app icon and native splash use a placeholder mark. See `docs/build-and-release.md`.
**Basis:** `docs/architecture.md` v0.2, `docs/tech-stack.md`, `docs/brand/tokens.json`, and the owner's answers of 9 Oct 2026: Android first and iOS later in Phase 0, mock data served by a deployed FastAPI, delivery by TestFlight and Play internal testing, application ID `in.priveo.app`, code in this repository, `dev` and `prod` environments until Phase 6.

## 1. The plan at a glance

| Phase | Features | 3rd party integrations |
|---|---|---|
| 0a: Android end to end | 1. Splash with animation. 2. One login screen. 3. Three mock logins: customer, crew, admin. 4. A home screen for each role. 5. Home screens built from mock data served by a deployed API. 6. Fully automated build, test, deploy and publish to Android devices | GitHub. AWS. A domain. Google Play Console. Google Cloud service account |
| 0b: iOS end to end | The same app and pipeline on iOS, delivered to iPhones through TestFlight | Apple Developer Program. App Store Connect. fastlane `match` |
| 1: Identity and reference data | Real sign-in for all three roles. Societies, plans, vehicle catalogue, services, slots, checklists. Admin web portal skeleton | AWS RDS, Secrets Manager, S3, CloudFront |
| 2: People | Admin creates customers, crew, vehicles, subscriptions. Customer email-code sign-in | Resend |
| 3: Scheduling | Scheduler, capacity, schedule board, freeze | Google OR-Tools |
| 4: Crew app | Job cards, checklists, photo and video proof, offline upload queue | AWS S3, CloudFront, Firebase Crashlytics |
| 5: Customer app | Onboarding, home, calendar, proof of service, account, push | Firebase Cloud Messaging, Apple APNs |
| 6: Changes and money | Skip, pause, UPI payments, invoices, Deep Spa, admin quick actions, `staging` | UPI ID and QR, GSTIN details, EventBridge Scheduler |
| 7: Support and feedback | Complaints, feedback, ratings, check-ins, admin alerts | Support phone numbers, Resend |
| 8: Hardening and launch | Load test, security review, store listings, production release | Privacy policy URL, store assets, Play and Apple review |

## 2. Phase 0 in detail

### 2.1 What you must arrange first (the build cannot start these steps without them)

| # | Item | Needed for | Lead time |
|---|---|---|---|
| 1 | AWS account with billing set up, and an admin user for me to deploy with through GitHub OIDC (no long-lived keys) | 0a API deploy | Same day |
| 2 | A domain you control (for `in.priveo.app` and for `api-dev`) and access to its DNS | 0a API address and certificate | Same day |
| 3 | Google Play Console account (about US$25 once), and the app `in.priveo.app` created | 0a Android delivery | A day or two for identity checks |
| 4 | Google Cloud service account with Play Console API access, as a JSON key stored in GitHub secrets | 0a automated Play upload | Same day, after item 3 |
| 5 | Apple Developer Program account (about US$99 a year) | 0b iOS delivery | Days. Start now |
| 6 | A private GitHub repository for iOS certificates, and an App Store Connect API key | 0b iOS signing and upload | Same day, after item 5 |
| 7 | Two or more test devices: one Android phone, one iPhone, added as testers | Testing | |

### 2.2 The three mock logins

Mock passwords are set as configuration on the dev API, never committed. The real admin password still comes from `.env` in Phase 1.

| Role | Sign-in ID (one field takes email, mobile or user ID) | Lands on |
|---|---|---|
| Customer | `customer@priveo.test` | Customer home |
| Crew | `9000000002` | Crew home |
| Admin | `priveopapa` | Admin quick-actions home |

A wrong ID or password shows the API's error message.

### 2.3 What each screen shows (mock data, modelled on the prototype)

| Screen | Content |
|---|---|
| Splash | Native splash (dark background, P mark), then an animated logo: fade and scale in, a gold rule draws under it, about 2 seconds, then to login or the role home. Skipped to a simple fade when the phone has reduce-motion on. Always dark. Each role has one look: customer dark (as the prototype), crew white, admin cream (owner decision, 10-Oct-26) |
| Login | Logo, one ID field, password field with show and hide, gold primary button (56 px high), error message area, and in dev builds a small "Use demo account" list |
| Customer home | Greeting, a vehicle card (registration, model, society, parking), the next service card (date, service, status), subscription status chip, four quick actions (Skip or Pause, Service History, Give Feedback, Report an Issue), bottom tabs Home, Calendar, Account, Support. Tabs other than Home show a "Coming soon" screen |
| Crew home | Date, society, counts for today (total, done, left), a list of job cards with time, vehicle, parking and service, and a status chip. No customer name or mobile number |
| Admin quick-actions home | Alert count, a list of payments to confirm, a needs-scheduling count, a sign-out button |

### 2.4 The mock API (FastAPI, deployed to AWS `dev`)

| Endpoint | Returns |
|---|---|
| `GET /v1/public/health` | OK, version, build number |
| `GET /v1/public/config` | Minimum app version |
| `POST /v1/auth/login` | Role, display name, mock access and refresh tokens, or the error envelope |
| `POST /v1/auth/refresh`, `POST /v1/auth/logout` | Mock token handling |
| `GET /v1/customer/home` | The customer home content above |
| `GET /v1/crew/home` | The crew home content above |
| `GET /v1/admin/home` | The admin home content above |

The API is built in its final shape: a router for each audience, a service layer and a repository interface. Phase 0 plugs in a mock repository. Phase 1 replaces it with the database and no route changes.

### 2.5 Work items, in order

| Step | Work | Output |
|---|---|---|
| 1 | Create the folder layout: `apps/mobile`, `services/api`, `packages/api-contract`, `.github/workflows`, `fastlane` | Empty skeletons that build |
| 2 | API: FastAPI app, health, config, mock login, three home endpoints, error envelope, request ID, tests, Dockerfile, OpenAPI export | Image runs locally, tests green |
| 3 | AWS `dev`: ECR, ECS Fargate service, load balancer, certificate, DNS name, log group, OIDC role for GitHub | `https://<api-dev-domain>/v1/public/health` responds |
| 4 | Pipeline for the API: on pull request lint and test, on merge build, push and deploy, then run the smoke test | A merge deploys the API with no manual step |
| 5 | Mobile skeleton: flavors `dev` and `prod`, Riverpod, go_router, Dio, folder structure from the architecture, strings through `l10n` | App starts on an emulator |
| 6 | Theme: a script turns `docs/brand/tokens.json` into the Dart light and dark themes. Bundle the Cormorant Garamond and Manrope files | Shared button, card and chip widgets |
| 7 | Splash (native and animated), login screen, role redirect guard, sign-out | Three logins reach three shells |
| 8 | Three home screens against the generated client and the deployed `dev` API | Homes show server data |
| 9 | Tests: unit tests for auth and mappers, widget tests for the screens, golden tests for the splash end state, login and the three homes in both themes, one `integration_test` that logs in as each role | Tests green in CI |
| 10 | Android release: application ID `in.priveo.app`, upload keystore in GitHub secrets, Play App Signing, fastlane `supply` to the internal testing track, build number from the run number | A merge puts a signed build in Play internal testing |
| 11 | 0b iOS release: macOS job, fastlane `match`, App Store Connect API key, fastlane `pilot` to TestFlight | A merge puts a build in TestFlight |
| 12 | Write the build and test commands into `CLAUDE.md`, and the pipeline in a short `docs/build-and-release.md` | A new developer can build from the docs |

### 2.6 The pipeline

| Workflow | Runs on | Does |
|---|---|---|
| `api-ci` | Pull request | Lint, pytest, contract check |
| `mobile-ci` | Pull request | `flutter analyze`, unit, widget and golden tests |
| `api-deploy` | Merge to `main` | Build image, push to ECR, deploy to ECS `dev`, smoke test: health, three mock logins, three home calls |
| `mobile-android-release` | Merge to `main` | Build signed bundle, publish to Play internal testing |
| `mobile-ios-release` | Merge to `main` (0b) | Build, sign, upload to TestFlight |

The mobile build uses the API address for `dev`. Secrets live in GitHub encrypted secrets and are never printed in logs or stored in the repository. Development is on Windows, so Android builds run locally and iOS builds run only in CI.

### 2.7 Phase 0 is done when

| Check | 0a (Android) | 0b (iPhone) |
|---|---|---|
| A merge to `main` runs the whole pipeline with no manual step and goes green | Yes | Yes |
| The build installs on a real device from the store test track | Play internal testing | TestFlight |
| The splash animates, then login appears | Yes | Yes |
| All three mock logins land on their own home | Yes | Yes |
| The home shows data from the deployed API, proven by changing a mock value on the API and seeing the app change | Yes | Yes |
| A wrong password shows the API's message | Yes | Yes |
| A deliberately broken test blocks the merge | Yes | Yes |

## 3. Phases 1 to 8 in detail

For each phase: what is built (modules, screens, endpoints), the requirement areas it covers, what you arrange, and how we know it is done.

### Phase 1: Identity and reference data

| Item | Detail |
|---|---|
| Backend | PostgreSQL and Alembic migrations. `identity` module (customer, crew and admin sign-in, passwords with Argon2, tokens, sessions, lockout, sign out of all devices). `directory` module (societies, plans, vehicle catalogue, services, working slots, checklists, could-not-complete reasons, settings). Seeded admin `priveopapa` with the password from `.env` |
| Mobile | The mock sign-in is replaced by real sign-in. Session handling and refresh. The homes stay on mock data until their modules exist |
| Web portal | React and Vite skeleton, cookie sign-in with CSRF, layout, theme from the tokens, screens for societies, plans, catalogue, services, slots, checklists, settings |
| Requirements | `ADM-ACC`, `ADM-SET`, `ADM-SVS`, `ADM-REF`, `CRW-ACC`, `AUTH-11` to `AUTH-17` |
| You arrange | AWS RDS, Secrets Manager, S3 and CloudFront for the portal, and a portal domain |
| Done when | An admin signs in on the web and the phone, edits reference data, and a wrong password locks after the set number of attempts |

### Phase 2: People

| Item | Detail |
|---|---|
| Backend | `crew` and `customers` modules. Crew password generated and shown once. Customer email code and welcome email through Resend |
| Mobile | Customer first sign-in with the emailed code, then password, then password reset |
| Web portal | Create and edit customers, vehicles, subscriptions and schedule settings. Create crew, set roles, working hours and exceptions. Reset and unlock logins |
| Requirements | `ADM-CUS`, `ADM-CRW`, `AUTH-`, `VEH-`, `SUB-` |
| You arrange | Resend account and sending domain with SPF, DKIM and DMARC |
| Done when | The admin creates a customer, the customer gets the email, signs in with the code and sets a password |

### Phase 3: Scheduling

| Item | Detail |
|---|---|
| Backend | `scheduling` module. OR-Tools solver as a pure function, capacity, Draft and Frozen schedules, manual changes kept on re-run, freeze and unfreeze with the secret code, needs-scheduling list. Runs in-process |
| Web portal | Run scheduler, schedule board with drag and drop, capacity view, freeze controls, needs-scheduling list |
| Requirements | `ADM-SCH`, `ADM-CAP`, `SCHED-` |
| You arrange | Nothing external |
| Done when | A Frozen schedule for one society and one week is produced from test data, and a manual change survives a re-run |

### Phase 4: Crew app

| Item | Detail |
|---|---|
| Backend | `visits` and `media` modules. Job status, checklist progress, signed upload URLs, could-not-complete records, manager endpoints |
| Mobile | Crew schedule and job cards, performing a service, checklist, photos and video with compression, offline upload queue with retry and resume on open, could-not-complete, manager features |
| Requirements | `CRW-SCH`, `CRW-SVC`, `CRW-CNC`, `CRW-MGR`, `CRW-PRF` |
| You arrange | S3 media bucket and CloudFront, Firebase project for Crashlytics, real crew devices |
| Done when | A crew member completes a day of jobs on a weak connection, and a job cannot complete until every upload is confirmed |

### Phase 5: Customer app

| Item | Detail |
|---|---|
| Backend | Customer reads of home, calendar, visit details and proof. `notifications` module with FCM and the in-app inbox |
| Mobile | Onboarding review steps, home, service calendar, service details with proof, service history, vehicles, account and settings, notifications, push |
| Requirements | `ONB-`, `HOME-`, `CAL-`, `SVC-`, `VEH-`, `NOTIF-` |
| You arrange | Firebase Cloud Messaging, Apple APNs key and push entitlement |
| Done when | A customer sees a completed visit with its photos and gets a push for it |

### Phase 6: Changes and money

| Item | Detail |
|---|---|
| Backend | `changes` (skip, un-skip, pause, cutoff requests, 9 PM rule for customers), `billing` (UPI flow, statuses, Due and Over due jobs, 7-day auto-Inactive, invoices), `addons` (Deep Spa). EventBridge jobs. `staging` environment |
| Mobile | Skip and pause, My Subscription, billing history, pay by UPI QR or ID and "I've paid", Deep Spa request, admin quick actions for payments and alerts |
| Web portal | Payments and invoices, add-on requests, subscription status |
| Requirements | `SKIP-`, `PAUSE-`, `PAY-`, `ADM-PAY`, `ADM-ADD`, `ADM-SUB` |
| You arrange | Business UPI ID and QR image, seller name, address and GSTIN, second AWS environment |
| Done when | A payment runs from Due to Received, and an unpaid one makes the subscription Inactive after 7 days |

### Phase 7: Support and feedback

| Item | Detail |
|---|---|
| Backend | `support` module: complaints, issues, feedback, ratings, check-ins. Admin alerts by push, bell and email |
| Mobile | Help and support, report an issue, my complaints, feedback, monthly check-in, crew ratings screen |
| Web portal | Complaints, feedback and ratings, check-in summaries, alert bell |
| Requirements | `ISS-`, `CMP-`, `FDBK-`, `CHK-`, `ADM-CMP`, `ADM-FDB`, `ADM-CHK`, `CRW-RAT`, `CRW-NOT` |
| You arrange | Helpline and WhatsApp numbers |
| Done when | A complaint goes from a customer to the admin and back with a status update |

### Phase 8: Hardening and launch

| Item | Detail |
|---|---|
| Work | Scheduler load test, security review of every route, accessibility pass, backup restore test, CloudWatch alarms, store listings, production release |
| You arrange | Privacy policy and support pages at public URLs, store listing assets, Play data safety form, Apple App Review with a demo login for each role |
| Done when | The release checklist is signed off and the app is live |

## 4. Flags

- `docs/tech-stack.md` still lists three environments. `staging` arrives in Phase 6, so that file needs a one-line note.
- The Phase 0 API serves mock data only. No database exists until Phase 1.
- The Apple account is the longest lead item. Start it now.
- Infrastructure as code (for example Terraform) is not chosen. **Open.** Phase 0 can create AWS resources by hand or with a short script.
- Google may require a closed-testing period before a new account can publish to production. Internal testing is not affected. Check the current rule when planning Phase 8.
- The first launch is one society. The data model stays multi-society.
