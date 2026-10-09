# Priveo Car Concierge: Technical Stack

**Status:** v0.2, 9 Oct 2026. The owner has decided every choice in sections 1 and 2. Section 4 lists risks to watch.
**Basis:** the three functional requirements files in `docs/reqs/`. Requirement IDs are cited where a requirement drives a choice.

## 1. Decided

| Area | Choice | Why it fits |
|---|---|---|
| Mobile app | Flutter, iOS and Android, one app for customer, crew and admin | `AUTH-10`, `ADM-ACC-04`. Role on the login decides the screens |
| App state and navigation | Riverpod, go_router, feature folders | Role-based routing, the vehicle switcher (`HOME-07`), testable state |
| API | Python, FastAPI, one service that also runs the scheduler | The scheduler needs OR-Tools. One codebase for the REST API, cron jobs, invoices and scheduling |
| Database | PostgreSQL | Relational rules: capacity, audit, billing, unique sign-in identifiers |
| Hosting | AWS Mumbai (ap-south-1): **ECS Fargate** for the API, RDS for Postgres, S3 for media, EventBridge Scheduler for cron jobs | Users are in India. ECS gives scheduled tasks and room for the scheduler |
| Email | Resend for the welcome email, verification codes and password reset codes. No SMS or WhatsApp provider in MVP | `AUTH-03`, `AUTH-16`, `ADM-CUS-04`. No passwords go by SMS or WhatsApp (`CRW-ACC-05`). Sending domain needs SPF and DKIM set up |
| Push notifications | Firebase Cloud Messaging on both platforms (APNs through FCM on iOS) | `NOTIF-01`, `NOTIF-02`, `ADM-SCH-24`, `CRW-NOT` |
| Media | S3 object storage with signed upload URLs | Photos under 10 MB and videos under 25 MB (rule 17), uploaded straight from the phone |
| Offline uploads | Local queue in the app, background upload with retry | `CRW-SVC-10`: uploads must survive a poor connection |
| Admin web (V2) | Flutter web, reusing the app's feature code and models | `ADM-ACC-01`, V2 portal. Design admin screens to work on tablet and desktop |

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
6. **API compatibility.** One app serves three roles, so older app versions stay in use. Version the API and plan for forced-update behaviour.
7. **Flutter, Dart and package versions.** Pin them when the project is created.
8. **Open owner choices:** none. Sections 1 and 2 are decided.
