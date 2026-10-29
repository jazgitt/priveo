# Priveo Car Concierge: Technical Architecture

**Status:** v0.3 DRAFT, 11 Oct 2026 (adds section 7.1, network and access checkpoints), for owner review. The owner answered the open architecture questions on 9 Oct 2026 (section 10). It builds on the decided stack in `docs/tech-stack.md`. The stack is not reopened here. Everything in this file is **Derived** from the stack and the requirements, or **Open**. Nothing is marked Owner.
**Basis:** the three requirements files in `docs/reqs/` and `docs/tech-stack.md`.
**Build order:** see `docs/build-plan.md`. For Phase 0 it supersedes the phase table in section 8.

## 1. Principles

1. **One backend, three audiences.** The mobile app (customer, crew, admin quick actions) and the web portal call one FastAPI service. Business rules live in one place, so a rule such as the 9 PM cutoff is written once (`ADM-ACC-10`).
2. **Modular monolith.** One deployable service, split into modules with clear borders. No microservices in MVP. A module can be pulled out later if the scheduler needs to scale alone.
3. **Transport is thin.** Routes only check the caller, parse input and call a service. Services hold the rules. This is what lets the web portal and the app share services.
4. **The server is the source of truth for rules and time.** Dates, cutoffs, freezes and statuses are decided on the server in India Standard Time. Clients display and ask.
5. **Contract first.** The OpenAPI schema is the contract. The Dart models and the TypeScript client are generated from it, so the apps cannot drift from the API.
6. **Offline only where it matters.** Crew uploads must survive a poor connection (`CRW-SVC-10`). Customers and admins are online-first with cached reads.
7. **Role decides the experience.** One login screen, one app. The role on the login picks the navigation shell.

## 2. System context

```
 Flutter app (iOS, Android)                 React web portal (admin)
 customer | crew | admin quick actions      all admin functions
        |  Bearer tokens                           |  HttpOnly cookie + CSRF
        |                                          |
        +-------------------+----------------------+
                            |  HTTPS, JSON, /v1
                     CloudFront / ALB
                            |
              +-------------+--------------+
              |   FastAPI service (ECS)    |
              |   routes -> services ->    |
              |   repositories             |
              |   + scheduler module       |
              +---+-----+------+------+----+
                  |     |      |      |
              Postgres  S3   Resend   FCM
               (RDS)  (media, (email) (push)
                      invoices)
                  ^
     EventBridge Scheduler -> ECS task (same image, job entry point)
```

## 3. Repository layout

One repository, so the contract, the apps and the tokens move together.

```
priveo/
  apps/
    mobile/            Flutter app (customer, crew, admin quick actions)
    admin-web/         React + TypeScript web portal
  services/
    api/               FastAPI service, scheduler, jobs
  packages/
    api-contract/      openapi.json (generated), generated Dart and TS clients
  docs/
    brand/tokens.json  design tokens, source for both UI themes
```

`docs/reqs/` and `docs/prototype/` stay as they are. **Owner:** the code lives in this repository, next to `docs/`. Keep commits that change code apart from commits that change requirements. Add the build and test commands to `CLAUDE.md` when code is added.

## 4. Backend architecture

### 4.1 Layers inside each module

| Layer | Job | Rule |
|---|---|---|
| Router | Parse the request, check the role, call a service, shape the response | No business rules |
| Service | Business rules and use cases, in one transaction | Knows nothing about HTTP. Called by routers, jobs and the scheduler |
| Repository | Database access with SQLAlchemy | Only services call it |
| Models and schemas | SQLAlchemy models (storage) and Pydantic schemas (API) | Kept apart, so the API can change without a migration |
| Policy | "May this user do this to this thing?" | One place for the role and ownership checks |

### 4.2 Modules

| Module | Owns | Used by | Requirement areas |
|---|---|---|---|
| `identity` | Logins, roles, passwords, email codes, sessions, lockout, seed admin | All three clients | `AUTH-`, `CRW-ACC`, `ADM-ACC` |
| `directory` | Societies, plans, vehicle catalogue, services, working slots, checklists, reasons, settings | Admin (write), apps (read) | `ADM-SET`, `ADM-SVS`, `ADM-REF` |
| `customers` | Customer profile, vehicles, parking, preferences, subscription state | Customer app, admin web | `ONB-`, `VEH-`, `SUB-`, `ADM-CUS` |
| `crew` | Crew profiles, roles, working hours, exceptions | Crew app, admin web | `CRW-`, `ADM-CRW` |
| `scheduling` | Schedules (Draft, Frozen), scheduled visits and jobs, the OR-Tools solver, capacity, needs-scheduling list, freeze rules | Admin web (run, review, freeze), apps (read) | `ADM-SCH`, `SCHED-` |
| `changes` | Skip, un-skip, pause, cutoff-time requests, with the 9 PM rule for customers and the admin exemption | Customer app, admin web | `SKIP-`, `PAUSE-`, `CAL-` |
| `visits` | Job status, checklist progress, media records, could-not-complete, completion rule | Crew app (write), customer app and admin (read) | `CRW-SVC`, `SVC-` |
| `billing` | Payments, statuses, add-on payments, invoices, UPI settings, due and over-due jobs | Customer app, admin web and quick actions | `PAY-`, `ADM-PAY` |
| `addons` | Deep Spa requests and their planning | Customer app, admin web | `ADM-ADD`, add-ons in the customer file |
| `support` | Complaints, issues, feedback, ratings, monthly check-ins | Customer app, crew (ratings read), admin web | `ISS-`, `CMP-`, `FDBK-`, `CHK-` |
| `notifications` | Push (FCM), email (Resend), admin alerts, notification settings, in-app inbox | Called by every module | `NOTIF-`, `ADM-SCH-24` |
| `media` | Signed upload and download URLs, size checks, the link between media and a visit | `visits`, `support` | rule 17 |
| `audit` | Append-only audit entries written with the change | Called by every module that changes data | audit rows in all three files |
| `platform` | Config, logging, errors, time (IST), clock, dependency wiring | All | |

**Border rules (Derived):**
- A module reads another module only through that module's service interface, never its tables.
- `notifications`, `audit` and `media` are called, and call nobody.
- `scheduling` is the only module that writes scheduled visits. `changes` and `addons` ask it to, so the rules stay in one place.
- Two modules never call each other in a circle. Where they would, publish a domain event (see 4.5).

### 4.3 How the web portal reuses the services

```
 customer route  POST /v1/customer/skips      -+
 admin route     POST /v1/admin/skips         -+--> changes.SkipService.skip(actor, vehicle, date)
 job (future)    ...                          -+         |
                                                          +-- rule: customer actor must act before 9 PM
                                                              admin actor is exempt, audit entry written
```

One service, several callers. The route decides who the actor is, the service applies the rule for that actor. This keeps the three requirement files consistent with one implementation.

### 4.4 API design

| Item | Choice | Status |
|---|---|---|
| Style | REST, JSON, resource-based, under `/v1` | Derived |
| Audience groups | `/v1/auth` (shared), `/v1/customer`, `/v1/crew`, `/v1/admin`, `/v1/public` (health, app config). Each group has its own router and role dependency | Derived |
| Contract | One OpenAPI schema per audience group, so the mobile app imports `customer`, `crew` and the admin quick actions, and the web portal imports `admin`. Smaller clients, clearer review | Owner: three schemas |
| Auth on mobile | Short-lived bearer access token, refresh token tied to a server session | Decided in the stack |
| Auth on web | HttpOnly secure cookie, CSRF token on every change request, 60 minute inactivity (`ADM-ACC-12`) | Decided in the stack and requirements |
| Errors | One envelope: `code` (stable, machine), `message` (plain, for display), `fields` (per-field errors), `request_id`. Clients map `code` to text | Derived |
| Lists | Cursor or page-and-size, server-side filter and sort on admin tables | Derived |
| Idempotency | An `Idempotency-Key` header on creating a skip, a payment status change, a media record and an add-on request, so a retry on a poor network never doubles it | Derived |
| Concurrency | `updated_at` version check on edited records. Last change wins where the requirements say so (`ADM-ACC-10`), but the audit keeps both | Derived |
| Versioning | `/v1` stays stable. Add fields, never change them. A minimum app version in `/v1/public/config` forces an update when needed | Derived |
| Time and money | ISO 8601 with offset on the wire, India Standard Time rules on the server. Money as integer paise, GST included | Derived |
| Rate limits | Per login and per IP on auth, code and password-reset routes | Derived |

### 4.5 Sketch of the main endpoints

| Group | Endpoints (examples) |
|---|---|
| `auth` | `POST /auth/login`, `/auth/email-code/request`, `/auth/email-code/verify`, `/auth/refresh`, `/auth/logout`, `/auth/password/reset-request`, `/auth/password/reset` |
| `customer` | `GET /me`, `PATCH /me`, `GET/POST /me/vehicles`, `GET /me/home`, `GET /me/calendar?month=`, `GET /visits/{id}`, `POST /skips`, `DELETE /skips/{id}`, `POST /pauses`, `GET /me/subscription`, `GET /me/payments`, `POST /payments/{id}/initiated`, `POST /addons/requests`, `POST/GET /complaints`, `POST /feedback`, `GET /notifications` |
| `crew` | `GET /me`, `GET /jobs?date=`, `GET /jobs/{id}`, `POST /jobs/{id}/start`, `PUT /jobs/{id}/checklist/{item}`, `POST /jobs/{id}/media` (returns a signed URL), `POST /jobs/{id}/media/{id}/confirm`, `POST /jobs/{id}/complete`, `POST /jobs/{id}/cannot-complete`, `GET /ratings`, plus Manager endpoints for their own society |
| `admin` | Customers, vehicles and subscriptions (CRUD and schedule settings), crew and logins, exceptions, services and slots, capacity, `POST /schedules/run`, `GET /schedules/{id}`, `PATCH /scheduled-visits/{id}`, `POST /schedules/{id}/freeze`, `POST /schedules/{id}/unfreeze`, needs-scheduling, payments and invoices, complaints, feedback, settings, session management, alerts |

Events inside the service (Derived): `VisitCompleted`, `PaymentStatusChanged`, `ScheduleFrozen`, `SkipCreated`, `ComplaintOpened`. They are in-process in MVP. `notifications` and `audit` listen. This keeps modules from calling each other in circles.

### 4.6 Data

| Item | Choice |
|---|---|
| Groups of tables | identity, directory, customers and vehicles, crew, scheduling, visits and media, billing, support, notifications, audit. Entity lists are in section 11 of the admin file, section 13 of the customer file and section 9 of the crew file |
| Rules in the database | Unique login identifiers, unique vehicle per customer, foreign keys everywhere, check constraints for statuses, a unique active schedule per society and date range |
| Audit | Append-only table written in the same transaction as the change |
| Migrations | Alembic, reviewed in pull requests, run as a step before deploy |
| Soft delete | Active flags rather than deletes for people, plans and reference data, since history must keep its names |
| Privacy | A crew member's API never returns a customer's name or mobile number. Enforced in the crew serializers and tested |

### 4.7 Scheduler module

| Item | Design |
|---|---|
| Shape | A pure function: `solve(inputs) -> proposal`. Inputs are customers' jobs, slots, crew hours and exceptions, capacity and the manual entries to keep. No database inside the solver |
| Runs | Started by the admin (`POST /schedules/run`). Runs as a background task and reports progress. Result is a **Draft** schedule |
| Manual changes | Entries marked "entered by hand" are fixed inputs on a re-run |
| Freeze | One transition, with the cutoff rules in a service. The admin secret code is checked on the server |
| Output | Scheduled visits, unscheduled visits with a reason (feeds needs-scheduling), and suggestions |
| Testing | Fixed scenarios as data files, so results can be compared between versions |
| Scale | Fine for one society and a week in a single task. Test with realistic volumes before sizing ECS tasks (risk 5 in the stack) |

### 4.8 Background jobs

The same container image with a job entry point. EventBridge Scheduler starts the ECS task. Jobs call services, never repositories.

| Job | Does |
|---|---|
| `billing.generate_due` | Creates Due payments for the next cycle, sends reminders |
| `billing.mark_overdue` | Moves unpaid to Over due, then makes the subscription Inactive after 7 days |
| `scheduling.freeze_reminder` | Warns the admin before the 8 PM freeze |
| `support.checkin_prompt` | Sends the monthly check-in push |
| `media.cleanup` | Removes unconfirmed uploads |
| `notifications.retry` | Retries failed pushes and emails |

All jobs are idempotent and safe to run twice.

## 5. Mobile architecture (Flutter)

### 5.1 Structure: feature-first, layered

```
apps/mobile/lib/
  main.dart, app.dart          bootstrap, flavors (dev, staging, prod)
  core/
    config/                    environment, flavors
    network/                   Dio client, interceptors (auth, retry, errors)
    storage/                   secure storage, Drift database
    auth/                      session, token refresh, role
    routing/                   go_router, role shells, guards
    ui/                        theme from tokens, shared widgets
    error/                     failure types, error mapping
    util/                      date (dd-Mon-yy, IST), money, validators
  features/
    auth/
    onboarding/                customer onboarding steps
    customer/
      home/  calendar/  visit_details/  skip_pause/
      subscription/  vehicles/  addons/  support/  notifications/
    crew/
      schedule/  job/  upload_queue/  ratings/  manager/
    admin_quick/
      alerts/  payments/  needs_scheduling/  sessions/
  l10n/
```

Each feature folder has the same shape:

```
feature/
  presentation/    screens, widgets, controllers (Riverpod notifiers)
  domain/          entities, repository interfaces, use cases (only where there is a rule)
  data/            repository implementations, API data sources, local data sources, DTO mappers
```

| Layer | Rule |
|---|---|
| Presentation | Widgets read state from Riverpod providers. No network calls, no business rules |
| Domain | Plain Dart. No Flutter or Dio imports. Easy to unit test |
| Data | The only layer that knows Dio, Drift or the generated API client. Maps DTOs to domain entities |

Dependency direction: presentation, then domain, then data implements domain. A feature never imports another feature's `data` or `presentation`. Shared things go in `core` or a small shared package.

### 5.2 State, navigation, dependency injection

| Area | Approach |
|---|---|
| State | Riverpod with `AsyncNotifier` per screen. Loading, data and error are always handled. Providers are scoped to the feature |
| Dependency injection | Riverpod providers. Repositories and the API client are injected, so tests replace them with fakes |
| Navigation | go_router with one **shell per role**: customer tabs (Home, My Vehicles, Support), crew shell (schedule, job, ratings), admin quick-action shell. A redirect guard sends an unsigned user to login and a signed user to their role's shell |
| Deep links and push | A notification carries a route. go_router opens it after the guard has checked the role |
| Models | `freezed` and `json_serializable`, generated from the OpenAPI contract where practical |

### 5.3 Offline and sync

| Area | Customer and admin quick actions | Crew |
|---|---|---|
| Reads | Cache the last good response in Drift. Show it with a "last updated" note when offline | Cache the day's job cards and checklists, so the shift can start without a signal |
| Writes | Online only. Show a clear message when offline | Checklist ticks and "could not complete" saved locally first |
| Media | Not applicable | **Upload queue**: file saved to app storage, a row in Drift, `workmanager` uploads in the background with retry, and the app also resumes the queue on open (iOS limits background work). A job cannot complete until every required upload is confirmed (`CRW-SVC-10`) |
| Conflicts | Server wins | Server wins, except that a recorded tick is never lost: the app retries until the server accepts it |

Upload steps: ask the server for a signed URL, upload straight to S3 with a size check, confirm to the API, delete the local copy. Photos and videos are compressed before upload.

### 5.4 Other mobile standards

| Area | Approach |
|---|---|
| Security | Tokens only in `flutter_secure_storage`. Certificate pinning is not in MVP (owner decision). No secrets in the app. Screens with personal data excluded from screenshots on request. Jailbreak and root detection are not in MVP (owner decision) |
| Errors | The data layer turns exceptions into typed failures. The UI shows the API's `message`. Crashes go to Crashlytics |
| Theming | One `ThemeData` for light and dark, built from `docs/brand/tokens.json`. Fonts are bundled. Follows the phone setting with a manual switch |
| Accessibility | 48 px touch targets (56 px on crew screens), 130% text scale, labels on every control, status never by colour alone |
| Localisation | English only in MVP. All strings still go through `l10n`, so a language can be added later (the customer file has a language setting) |
| Performance | Lists are paged and lazy. Images are resized by the server for lists. Cached images on disk |
| Release | Flavors for dev, staging and prod. A force-update gate reads the minimum version from `/v1/public/config`. Old app versions stay supported (risk 6 in the stack) |
| Testing | Unit tests for domain and data, widget tests for screens, golden tests for key screens in both themes, `integration_test` for the main flows per role |

## 6. Web portal architecture (React)

```
apps/admin-web/src/
  app/             router, providers, layout, theme from tokens
  api/             generated client (from the admin contract), query keys
  features/
    customers/  crew/  schedule-board/  capacity/  payments/
    complaints/  feedback/  settings/  alerts/  sessions/
  components/      table, filters, forms, dialogs (shadcn/ui based)
  lib/             auth (cookie session, CSRF), format (dd-Mon-yy, rupees)
```

| Area | Approach |
|---|---|
| Reuse | The portal reuses **backend services**, not UI code, as decided. It calls the `admin` routes, which call the same services as the app's routes |
| Data | TanStack Query, with query keys per feature and refetch after a change |
| Tables | TanStack Table with server-side filter, sort and paging |
| Forms | React Hook Form and Zod. Server `fields` errors map onto form fields |
| Schedule board | dnd-kit. A drag becomes `PATCH /scheduled-visits/{id}`. The server validates and returns the new state, so the board never decides a rule |
| Alerts | Bell with unread count, fed by an endpoint with server-sent events or polling, plus email |
| Theme | Light only (owner decision), from the same tokens |
| Auth | HttpOnly cookie session, CSRF header, 60 minute inactivity, sign out of all devices (`ADM-ACC-12`) |
| Hosting | Static build on S3 behind CloudFront, calls the API with CORS rules |

**What the app's admin quick actions reuse:** the same `admin` routes as the portal, so a payment confirmed on a phone is the same call as on the web (`ADM-ACC-07`, `ADM-ACC-10`). The list of quick actions can shrink without a backend change (`ADM-ACC-11`).

## 7. Cross-cutting concerns

| Area | Approach |
|---|---|
| Authorisation | Role dependency on each router group, then a policy check in the service: ownership (a customer sees only their own data) and scope (a Manager acts only in their own society) |
| Notifications | `notifications` module with a template per event. Delivery by FCM and Resend with retry. User settings respected. A record in an inbox table feeds the in-app list and the bell |
| Media access | Private bucket. Signed URLs with a short life. Customers receive URLs only for their own visits |
| Audit | Every admin change and every status change writes an audit entry in the same transaction |
| Observability | Structured JSON logs with `request_id` and user role (no personal data), CloudWatch alarms, Sentry or Crashlytics for errors |
| Config and secrets | Environment variables and AWS Secrets Manager. The admin password comes from `.env` at seed time and is never committed |
| Environments | `dev` and `prod` from the start, each with its own database and bucket. `staging` is added in phase 6 (owner decision), before payments and store submission |

### 7.1 Network and access checkpoints

**Target (Derived from the reviewer's security requirement, not an Owner decision):** one public entry point to the backend. The database and every other backend part are private. Use this list for the move from `dev` to `prod` and in each security review. Mark each line with the date and who checked it.

**What `test` and `prod` are (29 Oct 2026).** Since 29 Oct 2026 the API runs as two Vercel projects in the `priveo` team, `priveo-api-test` and `priveo-api-prod`, both in Mumbai (`bom1`), each with its own Supabase PostgreSQL database in Mumbai (`docs/build-and-release.md`). A Supabase database is reached over the public internet with TLS and credentials only, and GitHub Actions connects to it directly to migrate and seed. So neither meets the private-subnet target below. The owner chose this setup on 29 Oct 2026 as the first step: **Supabase first, then AWS Mumbai with a private RDS later**, as the owner decision of 19 Oct 2026 says (`docs/hosting-assessment/README.md`). So the Supabase `prod` is interim and the checkpoints below stay the bar for the AWS `prod`. The AWS path stays in the repo (`DEPLOY_PROVIDER=aws`).

| # | Checkpoint | Pass when |
|---|---|---|
| N1 | Single public entry | The only public endpoint to the backend is the load balancer (optionally behind CloudFront with WAF). TLS only, HTTP redirects to HTTPS. No other public IP or DNS name reaches the backend |
| N2 | API tasks are private | ECS Fargate tasks run in private subnets with no public IP. Their security group accepts traffic only from the load balancer's security group |
| N3 | Database is private | RDS has `PubliclyAccessible=false` and sits in private subnets. Its security group accepts port 5432 only from the API's security group (or RDS Proxy, which accepts only the API). No `0.0.0.0/0` rule |
| N4 | Database encrypted | Encryption at rest is on. Connections require TLS. Automated backups are on, and the restore test of phase 8 has passed |
| N5 | No DB route from CI or laptops | GitHub Actions has no `DATABASE_URL` for `prod`. Migrations and seeding run as a one-off ECS task inside the VPC. Admin access to the database is through a break-glass path (SSM Session Manager or a bastion with no public SSH), logged, and off by default |
| N6 | CI deploys by OIDC | GitHub Actions assumes an AWS role by OIDC with least privilege. No long-lived AWS keys in GitHub |
| N7 | Secrets | Database password, `TOKEN_SECRET`, the Resend and FCM keys live in Secrets Manager and are injected into the task. None are in the repo, the image, GitHub secrets for `prod`, or logs. The admin password comes from the environment at seed time only |
| N8 | Outbound only as needed | Private subnets reach Resend and FCM through a NAT gateway. S3 is reached through a VPC gateway endpoint. Security groups allow no other outbound by default where practical |
| N9 | Scheduler and jobs stay inside | EventBridge Scheduler starts tasks inside the VPC. It does not call a public URL. The in-process scheduler (section 10, decision 3) needs no inbound path |
| N10 | Media bucket | The S3 bucket blocks all public access. Access is by short-lived signed URLs only. Uploads restrict content type and size, and use a prefix per visit. Customers get URLs only for their own visits. This is the one deliberate second public path, because the app talks to S3 directly for uploads; keep it narrow |
| N11 | Edge protection | WAF with rate limits on the sign-in and code endpoints. Lockout and rate limits also hold in the API |
| N12 | Separate environments | `prod` has its own VPC or account, database, bucket and secrets. `dev` credentials never work on `prod`, and `prod` data is never copied to `dev` |
| N13 | Logs and alarms | Load balancer, WAF and VPC flow logs go to CloudWatch. Alarms fire on repeated 401s, 5xx spikes, and any change to a security group, the RDS public flag or the bucket policy |
| N14 | No stray public parts | No public admin or docs route in `prod` (turn off `/docs` and `/openapi.json` or protect them). No debug endpoints. The fixed dev sign-in code (`MOCK_EMAIL_CODE`) is off in `prod` |

**Security review procedure.** Before launch and at each review: (1) list public endpoints from DNS, the load balancer, security groups and the bucket policy, and confirm only N1 and N10 appear; (2) try a connection to the database port from outside the VPC and expect it to fail; (3) confirm the checkpoints in the table and record the date. A failed line blocks release.

**Open:**
- Whether `prod` uses its own AWS account or a separate VPC in one account. Decide before the AWS build.
- Whether to use CloudFront in front of the load balancer in MVP, or only the load balancer with WAF.
- When to move `dev` to AWS too, so `dev` and `prod` have the same network shape (`DEPLOY_PROVIDER=aws` already supports it).

## 8. Build plan

Phases follow the dependencies: a customer cannot sign in until an admin has created them, and the crew have no jobs until the scheduler has run. So the admin data and the scheduler come early, even though customers are the larger audience.

| Phase | Build | Done when |
|---|---|---|
| 0 Foundation | Repository, CI (lint, test, build), Docker, the `dev` and `prod` environments, FastAPI skeleton with the error envelope and OpenAPI export, Flutter skeleton with flavors, theme from tokens and role shells, React skeleton, generated clients, `platform` and `audit` modules | A "hello" call from the app and the portal reaches the API in `dev`, and CI is green |
| 1 Identity and reference data | `identity` (all three sign-ins, email codes, sessions, lockout, seed admin), `directory` (societies, plans, catalogue, services, slots, checklists), the admin portal sign-in and settings screens | An admin signs in on the web and the app, and can manage reference data |
| 2 People | `crew` and `customers` modules, admin screens for customers, vehicles, subscriptions, crew, working hours and exceptions, crew password hand-over | The admin can create a customer and a crew member, and the customer can sign in |
| 3 Scheduling | `scheduling`, solver, capacity, schedule board, freeze and unfreeze, needs-scheduling | A frozen schedule for one society and a week is produced from test data |
| 4 Crew app | Job cards, performing a service, checklist, offline upload queue, could-not-complete, manager features, `visits` and `media` | A crew member completes a day of jobs with a poor connection |
| 5 Customer app | Onboarding, home, calendar, service details with proof, vehicles, account, notifications | A customer sees a completed visit with its photos |
| 6 Changes and money | `changes` (skip, pause, cutoff), `billing` (UPI flow, statuses, jobs, invoices), `addons`, admin payment screens and quick actions, and the `staging` environment | A payment runs from Due to Received, and an over-due payment makes the subscription Inactive after 7 days |
| 7 Support and feedback | `support` (complaints, issues, feedback, ratings, check-ins), admin alerts, ratings shown to crew | A complaint goes from a customer to the admin and back |
| 8 Hardening | Load test of the scheduler, security review, accessibility pass, backup restore test, store submissions | The release checklist is signed off |

The requirements start each ID at **Draft**. As each phase starts, move its IDs to Backlog and Ready for Dev with `/fstatus`, so the status board follows the build.

## 9. Testing strategy

| Level | Backend | Mobile | Web |
|---|---|---|---|
| Unit | Services and the solver, with fake repositories. Target above 95% on rules | Domain and data layers | Hooks, formatters |
| Component | Routers with a test database | Widget tests, golden tests in both themes | React Testing Library |
| Contract | Schema diff in CI fails the build on a breaking change to `/v1` | Generated clients compile | Generated client compiles |
| End to end | A scripted day: admin creates, schedule runs and freezes, crew completes, customer sees | `integration_test` per role | Playwright for the main admin flows |
| Security | Role and ownership tests on every route, crew privacy test, rate limits | Token storage checks | Cookie, CSRF and session tests |

## 10. Decisions and open items for this design

Owner decisions of 9 Oct 2026:

1. **Code location:** this repository.
2. **API contract:** three OpenAPI schemas (customer, crew, admin).
3. **Scheduler runs:** in-process background task on the API service, behind the `solve` function. Move to a separate ECS task later if volumes need it.
4. **Admin bell:** polling first, server-sent events later.
5. **Mobile hardening:** no certificate pinning and no root or jailbreak detection in MVP. Revisit after launch.
6. **First launch:** one society. The data model stays multi-society, so adding a society needs no migration. Scheduling and capacity are built and tested for one society first.
7. **Environments:** `dev` and `prod` from the start, `staging` added in phase 6. This phases the three environments in `docs/tech-stack.md`; the end state is unchanged.

Still open or to watch:

1. **Phone deep links** from push notifications into each role's screens need a route list. Derived when the screens are built.
2. **Admin single login** remains the main security risk (risk 8 in the stack).
