# Priveo Car Concierge: Technical Stack

**Status:** v0.3, 9 Oct 2026. The owner has decided every choice in sections 1, 2 and 5. Section 6 (design system) is a draft awaiting review. Section 4 lists risks to watch.
**Basis:** the three functional requirements files in `docs/reqs/`. Requirement IDs are cited where a requirement drives a choice.

## 1. Decided

| Area | Choice | Why it fits |
|---|---|---|
| Mobile app | Flutter, iOS and Android, one app for customer and crew, plus a limited set of admin quick actions | `AUTH-10`, `ADM-ACC-04`, `ADM-ACC-07`. Role on the login decides the screens |
| App state and navigation | Riverpod, go_router, feature folders | Role-based routing, the vehicle switcher (`HOME-07`), testable state |
| API | Python, FastAPI, one service that also runs the scheduler | The scheduler needs OR-Tools. One codebase for the REST API, cron jobs, invoices and scheduling |
| Database | PostgreSQL | Relational rules: capacity, audit, billing, unique sign-in identifiers |
| Hosting | AWS Mumbai (ap-south-1): **ECS Fargate** for the API, RDS for Postgres, S3 for media, EventBridge Scheduler for cron jobs | Users are in India. ECS gives scheduled tasks and room for the scheduler |
| Email | Resend for the welcome email, verification codes and password reset codes. No SMS or WhatsApp provider in MVP | `AUTH-03`, `AUTH-16`, `ADM-CUS-04`. No passwords go by SMS or WhatsApp (`CRW-ACC-05`). Sending domain needs SPF and DKIM set up |
| Push notifications | Firebase Cloud Messaging on both platforms (APNs through FCM on iOS) | `NOTIF-01`, `NOTIF-02`, `ADM-SCH-24`, `CRW-NOT` |
| Media | S3 object storage with signed upload URLs | Photos under 10 MB and videos under 25 MB (rule 17), uploaded straight from the phone |
| Offline uploads | Local queue in the app, background upload with retry | `CRW-SVC-10`: uploads must survive a poor connection |
| Admin web portal (MVP) | A separate React web app in TypeScript, calling the same FastAPI service. A typed client is generated from the API's OpenAPI schema. The portal shares the API with the mobile app, not UI code | `ADM-ACC-01`, `ADM-ACC-08`. Data tables, filters, drag and drop for the schedule board, charts |

## 2. Supporting choices (decided)

### App

| Area | Choice | Notes |
|---|---|---|
| HTTP client | Dio with interceptors for tokens, retry and error mapping | |
| Models and JSON | `freezed` and `json_serializable` | Generated from the API's OpenAPI schema where practical |
| Local database | Drift (SQLite) | Upload queue, cached lists and last-known schedule for crew |
| Background work | `workmanager` for background upload and `flutter_local_notifications` for foreground push display | iOS background limits are strict, so the upload queue must also resume on app open |
| Camera and media | `image_picker` plus `camera`, `video_compress`, `flutter_image_compress` | HEIC accepted (rule 17). Compress before upload to stay under the limits |
| Secure storage | `flutter_secure_storage` for tokens | |
| Calls and WhatsApp | `url_launcher` | `SUP-02`, `SUP-03` |
| UPI QR and ID | Show the QR image and a copyable UPI ID, no payment SDK | `PAY-05`: MVP has no payment gateway |
| Dates | `intl`, one shared formatter for `dd-Mon-yy` | Rule 28 in the customer file. India Standard Time throughout |
| Error and crash reports | Firebase Crashlytics | |
| Testing | `flutter_test`, `integration_test`, golden tests for key screens | |

### API

| Area | Choice | Notes |
|---|---|---|
| Web framework | FastAPI with Pydantic v2 | Auto-generated OpenAPI used to produce the Dart client or models |
| Database access | SQLAlchemy 2 and Alembic migrations | |
| Authentication | Short-lived JWT access tokens plus refresh tokens. Customers by email: an emailed code on first sign-in, then email and password. Crew by mobile number and password. Admins by user ID and password. Passwords hashed with Argon2 | `CRW-ACC-02`, `AUTH-11` to `AUTH-17`. One login field takes an email, a mobile number or a user ID. Role claim decides access. Rate limit and lockout (`CRW-ACC-07`). The admin shows a crew password once and it is never stored readable |
| Sessions | A server-side session record for each sign-in, with device details and last-active time. Short-lived access tokens, with the refresh token tied to the session so it can be ended at once | `ADM-ACC-14`, `ADM-CRW-21`, `ADM-ACC-13`, `CRW-ACC-11`. Inactivity sign-out (60 minutes on web, 24 hours for admin on mobile) is enforced on the server |
| Authorisation | Role checks on every route: customer, crew (with Manager, Member, Trainee), admin | `CRW-MGR`, `ADM-ACC-02`. A Manager acts only within their own society |
| Scheduler | Google OR-Tools (CP-SAT) behind an internal module | `ADM-SCH`: maximise crew capacity, keep manual changes on re-run, flag cutoff misses, suggest improvements |
| Background jobs | AWS EventBridge Scheduler triggering ECS tasks, or an in-process scheduler (APScheduler) on one instance | Monthly Due payments, Over due, 7-day auto-Inactive, renewal reminders, check-in pushes |
| Invoices | WeasyPrint or ReportLab for the GST invoice PDF, stored in S3 | `ADM-PAY-08`, `ADM-PAY-09`. Seller details come from the seed |
| Audit | An append-only audit table written in the same transaction as the change | `ADM-SCH-19`, `ADM-PAY-05`, `ADM-CUS-16`, `CRW-MGR` |
| Secret code | Checked on the server, stored hashed in configuration | `ADM-SCH-18` |
| Configuration | Environment variables, AWS Secrets Manager for keys | Never commit secrets |

### Platform and delivery

| Area | Choice | Notes |
|---|---|---|
| Containers | Docker images built in CI and run on ECS Fargate (decided) | Cron work through EventBridge Scheduler |
| Database | RDS PostgreSQL, Multi-AZ off in MVP, automated backups on | |
| Media | One private S3 bucket. Signed upload and download URLs. CloudFront in front for the app's reads | Customers see only their own visit media |
| Environments | `dev`, `staging`, `prod` with separate databases and buckets | |
| CI/CD | GitHub Actions: Flutter analyse and test, Python lint and test, build and deploy | |
| Seed data | The admin account (user ID `priveopapa`, password from `.env`), seller invoice details, plans, societies, vehicle catalogue, checklists | Admin account and invoice details are seeded by decision (`ADM-ACC-05`, `ADM-SET-04`). The password never goes in the repository |
| Observability | CloudWatch logs and alarms, Sentry or Crashlytics for errors | |

## 3. Requirement areas and the pieces that serve them

| Requirement area | Served by |
|---|---|
| Login by role, email code and password | FastAPI auth, Resend, JWT |
| Onboarding, plans, vehicles, societies | Flutter feature folders, FastAPI, Postgres reference tables seeded and admin-managed |
| UPI payment, statuses, reminders, auto-Inactive | Manual UPI flow, Postgres payment records, scheduled jobs, FCM |
| Calendar, skip, pause, 9 PM rule | Server-side date rules in IST, so the app and the admin see one truth |
| Scheduler and freeze | OR-Tools module, schedule tables with Draft and Frozen, audit trail |
| Crew job cards, checklists, proof | Flutter, S3 signed uploads, Drift upload queue |
| Complaints, feedback, check-ins | Postgres, FCM for complaint updates |
| Invoices | WeasyPrint or ReportLab, S3 |

## 4. Risks and decisions still needed

1. **Apple and Google setup.** An Apple Developer account is needed for push and release. Allow lead time.
2. **Email delivery.** Verification and reset codes depend on email arriving. Set up SPF and DKIM on the sending domain, watch bounces, and test with Gmail and Outlook before launch. Customers who cannot receive email need the admin reset (`ADM-CUS-19`, `ADM-CUS-20`).
3. **Hand-over of crew passwords.** They are shown once to the admin and given out in person, so a lost password means a reset. Consider a short-lived "must be handed over" reminder in the admin screen.
4. **iOS background upload.** Crew uploads may pause when the app is closed. The queue must resume on open, and the job must stay not complete until everything has uploaded (`CRW-SVC-10`).
5. **Scheduler scale.** OR-Tools CP-SAT is fine for one society and a week. Test with realistic volumes before choosing ECS task sizes.
6. **API compatibility.** The mobile app serves customers, crew and the admin quick actions, so older app versions stay in use. Version the API and plan for forced-update behaviour. The web portal can always be updated at once.
7. **Flutter, Dart and package versions.** Pin them when the project is created.
8. **Admin web portal security.** The portal holds every admin power, behind one user ID and password. Decided for the first release: HttpOnly cookies with CSRF protection and short sessions (`ADM-ACC-12`). Not yet decided and listed as V2: two-factor sign-in for admins, and an IP allowlist or AWS WAF rules in front of the portal. These are the main risk of the single admin login, so revisit them soon after launch. Dev and prod are separate deployments; the prod task definition must set `ENVIRONMENT=prod` and the server refuses to start with dev-only settings (`docs/build-and-release.md`).
9. **Open owner choices:** the vector logo files (to follow) in section 6. Sections 1, 2 and 5 are decided.

## 5. Admin web portal: supporting choices (decided)

| Area | Choice | Notes |
|---|---|---|
| Framework | React with TypeScript, built with Vite | An internal tool, so no server-side rendering is needed |
| Data fetching | TanStack Query | Caching, refetch after changes, optimistic updates |
| Tables | TanStack Table, with server-side filtering and paging | Payments, complaints, customers, crew, add-on requests, feedback |
| Forms | React Hook Form with Zod validation | Customer creation, working-hours grid, settings |
| Routing | React Router | |
| UI kit | Tailwind CSS with shadcn/ui components | Accessible, consistent, quick to build |
| Schedule board | dnd-kit for drag and drop between crew and times | `ADM-SCH-12`, `ADM-SCH-13` |
| Charts | Recharts | Capacity against demand, feedback and check-in summaries |
| API client | Generated from OpenAPI (openapi-typescript or Orval) | Keeps the web portal and API in step |
| Hosting | Static build on S3 behind CloudFront, same AWS account | Cross-origin calls to the API need CORS rules |
| Alerts | Notification bell fed by an API endpoint with server-sent events or polling, plus Resend emails | `ADM-ACC-09` |
| Testing | Vitest and React Testing Library, Playwright for key flows | |
| CI/CD | GitHub Actions: lint, test, build, deploy to S3 and invalidate CloudFront | |

## 6. Design system and brand guide (DRAFT for owner review)

**Source:** the design theme comes from the customer app prototype only (`docs/prototype/Priveo Customer App Prototype.html`). The wireframe images are not used for the look. Owner answers of 9 Oct 2026 are marked **Owner**. Values read from the prototype are **Derived**. Anything not in the prototype is **Open**.

### 6.1 Owner decisions

| Decision | Status |
|---|---|
| The dark and gold look of the prototype is the final brand look | Owner |
| Brand fonts are Cormorant Garamond (display) and Manrope (body) | Owner |
| A light mode is needed (customer and crew) | Owner |
| The admin web portal uses a light theme | Owner |
| The "CC" monogram is retired. The Priveo logo is the only logo | Owner |
| The tagline "Own the Car. We'll Handle the Rest." stays in use | Owner |
| The design theme is taken from the prototype only, not from the wireframes | Owner |

### 6.2 Logo

| Item | Rule | Status |
|---|---|---|
| Primary logo | The Priveo logo in the prototype: a stylised "P" with a car swoosh, the word PRIVEO in wide-spaced capitals with a gold "O", and "CAR CONCIERGE" in gold between two thin gold rules | Derived |
| Colours | White and gold on black or dark backgrounds. On light backgrounds use a dark ink and gold version | Derived. The light-background version comes with the vector files |
| Retired mark | The "CC" monogram and the "Car Concierge, Premium Vehicle Care" lockup. The Priveo logo is the only logo | Owner |
| Master file | Only a 278 x 100 px transparent PNG is in the repo (`docs/brand/priveo-logo.png`, taken from the prototype). It is too small for the app icon, splash screen or print | Owner: use this PNG for now. The vector master (full logo and "P" mark alone) comes later and goes in `docs/brand/` |
| App icon and splash | The "P" mark alone, gold on `ink`. The splash screen shows the full logo on `ink` | Derived |
| Clear space and size | Clear space around the logo is at least the height of the letter "P" in the wordmark. Minimum width 96 px on screen | Derived (a suggested rule, not in the sources) |
| Do not | Stretch it, recolour it, add effects, or place it on a busy photo without a dark overlay | Derived |

### 6.3 Colour

Dark theme (the prototype). Tokens are named so the same names work in light theme.

| Token | Dark | Use | Status |
|---|---|---|---|
| `ink` | `#08080A` | Backdrop, splash | Derived |
| `app` | `#0D0D10` | App background | Derived |
| `card`, `card2` | `#151519`, `#1C1C21` | Cards, raised cards | Derived |
| `line` | `#2A2925` | Borders, dividers | Derived |
| `hair` | `rgba(201,165,92,.20)` | Fine gold outlines | Derived |
| `text` | `#F4F0E8` | Main text | Derived |
| `mute`, `dim`, `grey` | `#A39D92`, `#6E695F`, `#77736B` | Secondary, tertiary, disabled text | Derived |
| `gold` (`gold-hi` `#E9D09A`, `gold-lo` `#9C7A3A`) | `#C9A55C` | Brand accent, primary button | Derived |
| `wine` (`wine-hi` `#B0414F`) | `#7D1F2E` | Secondary accent | Derived |
| `ok` | `#62C391` | Success, completed | Derived |
| `warn` | `#E8A951` | Warning, due | Derived |
| `info` | `#6A97F2` | Information, scheduled | Derived |
| `spa` | `#BC8CF2` | Deep Spa service | Derived |
| `error` | `#F08F9B` | Errors, over due | Derived (a light red that appears in the prototype) |

Light theme. The prototype has no light theme, so this one is built from the prototype's own colours: the same gold and wine, with the neutrals inverted and the status colours darkened for contrast on white. Every light value is a proposal. The owner has decided that a light mode exists (customer, crew and the admin portal), not what it looks like.

| Token | Light | Use | Status |
|---|---|---|---|
| `app` | `#F7F3EC` | Page background, a warm tint of the prototype's `text` colour | Owner (approved) |
| `card` | `#FFFFFF` | Cards, inputs | Owner (approved) |
| `line` | `#E4DDD0` | Borders, dividers | Owner (approved) |
| `text` | `#16151A` | Main text, close to the prototype's `app` | Owner (approved) |
| `mute` | `#6B665D` | Secondary text | Owner (approved) |
| `gold` | `#C9A55C` for fills, `#8A6A2C` for gold text and icons | The prototype gold is too pale as text on white | Derived (fill), Owner (approved text colour) |
| `wine` | `#7D1F2E` | Secondary accent, titles, selected state | Derived |
| `ok`, `warn`, `info`, `spa` | `#2E9E6B`, `#C98A2B`, `#3F6FD8`, `#8A4FD0` | Status colours, darkened for white | Owner (approved) |
| `error` | `#C0392B` | Errors, over due | Owner (approved) |

Rules:
- The primary action is the gold button in both themes, with dark text `#1B1408`. Wine is the secondary accent.
- Status colours keep the same meaning in both themes.
- Colour is never the only signal. A status always has a text label.
- Text must reach 4.5:1 contrast. `dim` and `grey` on `card` in dark theme are likely below that, so they are for disabled or decorative text only. **Open:** run a contrast check before build.

### 6.4 Type

| Item | Rule | Status |
|---|---|---|
| Display | Cormorant Garamond 500, 600, 700, 500 italic. Used for screen titles and large numbers, from 20 px up. Never for small text | Owner (fonts), Derived (use) |
| Body | Manrope 400 to 800. Used for everything else | Owner (fonts), Derived (use) |
| Scale | 11, 12, 13, 14, 16, 18, 22, 28 px. The prototype uses 11 to 18 px in half steps; this trims it to one scale | Owner (approved) |
| Fallbacks | Georgia, then system sans | Derived |
| In Flutter and the portal | Bundle the font files (works offline, no network fetch on first launch). The web portal self-hosts the same files | **Open** |
| Text size | Layouts must hold up at 130% system text size | Derived |

### 6.5 Shape, depth and components

| Item | Rule | Status |
|---|---|---|
| Corner radius | 12 px inputs and small cards, 18 px cards, 22 px sheets, 17 px buttons, 50% avatars | Derived |
| Primary button | 56 px high, full width, 700 weight, 16 px. Gold gradient (`#EFD7A2`, `#C9A55C`, `#AD8743`) with dark text `#1B1408`, in both themes | Derived |
| Secondary button | Transparent with a 1 px `line` border and `text` colour. A wine button (gradient `#9A2C3C` to `#7D1F2E`, light text) is used for firm actions such as confirming a skip | Derived |
| Pressed state | Scale 0.97, brightness 0.92 | Derived |
| Depth | Soft gold glow under the primary button (dark), 1 px hairlines on cards. No heavy shadows | Derived |
| Sticky footer | The main action is pinned at the bottom with a fade into `app` | Derived |
| Status chip | Small rounded chip with a colour tint and a text label. Deep Spa uses `spa`, completed uses `ok`, due uses `warn`, scheduled uses `info` | Derived |
| Icons | Outline icons, 1.5 px stroke, one set only | Owner: Material Symbols Rounded |
| Touch targets | At least 48 px. Crew screens use 56 px or larger, since they are used outdoors, often with wet hands | Derived |
| Motion | Short (150 to 250 ms), no decorative animation | Derived |

### 6.6 Voice

| Item | Rule | Status |
|---|---|---|
| Tagline | "Own the Car. We'll Handle the Rest." | Owner |
| Tone | Calm, polite, concise. Plain short sentences, English only | Derived (matches the requirements rules) |
| Dates and money | `dd-Mon-yy`, and rupees with GST included | Owner (existing rule) |
| Photos | Real cars in society parking, clean and well lit. No stock luxury imagery that does not match the customer's car | Derived |

### 6.7 How it maps to the stack

| Area | Proposal | Status |
|---|---|---|
| Source of truth | One file, `docs/brand/tokens.json`, holding colours, type, radii and spacing for both themes. The Flutter theme and the Tailwind config are generated from it | Done: the file exists. Generating the themes from it happens when the apps are built |
| Flutter app | Material 3 `ThemeData` (light and dark) built from the tokens, a `ThemeExtension` for gold, wine and status colours, and shared widgets (button, card, status chip) in `core/ui`. Theme follows the phone setting, with a manual switch in Settings | **Open** |
| Admin web portal | Tailwind theme and shadcn/ui CSS variables from the same tokens. Light theme only (owner decision) | **Open** |
| Golden tests | Golden tests for key screens run in both themes | **Open** |
| Brand folder | `docs/brand/` holds the logo files and tokens. `docs/prototype/` stays read-only | Derived |

### 6.8 Still needed from the owner

1. The vector logo files (full logo, "P" mark alone, light-background version), to be added to `docs/brand/` later. The PNG is used until then.
