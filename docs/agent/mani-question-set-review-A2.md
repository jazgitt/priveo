# Mani Bond: golden question set, part A2

Part A2: code implementation, questions 11 to 20. Run and clear on its own with `--set A2` (`services/api/tests/mani_eval`). The overview, the review rules and the points to settle are in [`mani-question-set-review.md`](mani-question-set-review.md).

This file is part of the evaluation answer key. It stays out of the search index (`services/api/app/mani/sources.py`, `EXCLUDE_PATHS`). Do not remove that exclusion, or Mani will find its own answers.

## A. Code implementation (sources: `services/api`, `wiki/`) - part 2 (questions 11 to 20)

| # | Question | Golden answer | Source | Decision | Notes |
|---|---|---|---|---|---|
| 11 | How is a crew member's first password generated? | `generate_password`: the first 3 letters of the name capitalised (padded with `x` if shorter), then 4 random digits from `secrets`, then `$`. Example `Raj4821$`. | `app/crew/service.py`, `wiki/Workforce_management.md` | Keep | |
| 12 | Where are the 8 PM freeze and the 9 PM customer cutoff set? | 8PM is last custof time for customer to request a skip or pause. 9PM is the scheduler cut off time for next day's run | `app/scheduling/rules.py`, `app/changes/rules.py`, `wiki/Scheduling_and_capacity.md`, `wiki/Skips_and_pauses.md` | Drop | |
| 13 | What are the upload size limits for media? | Photo 10 MB, video 25 MB, document 5 MB (`MAX_BYTES` in `app/media/service.py`). | `app/media/service.py`, `wiki/Service_execution_and_proof.md` | Keep | |
| 14 | What does the server check at startup, and what stops it from starting? | `startup_problems`: `TOKEN_SECRET` must be set (not a placeholder). `ENVIRONMENT` must be exactly `dev`, `test` or `prod`, and a hosted server must set it. In prod: the secret needs a minimum length, dev-only settings (`SEED_DEMO_LOGINS`, `MOCK_EMAIL_CODE`, mock passwords) must be unset, and `RESEND_API_KEY` and `CRON_SECRET` must be set. | `app/platform/config.py`, `wiki/Deployment_and_hosting.md`, `wiki/Security.md` | Keep | |
| 15 | Which scheduled jobs does the API expose, and where do they run? | Eight cron routes under `/v1/internal/cron/`: `crew-society-moves`, `automatic-planning`, `freeze-due`, `payments-generate`, `payments-overdue`, `renewal-reminders`, `checkin-notify`, `complaints-overdue`. Vercel runs them in region `bom1` (Mumbai). The Mani retention job uses the same route with `Authorization: Bearer $CRON_SECRET`. | `vercel.json`, `app/mani/cron.py`, `wiki/Notifications.md`, `wiki/Deployment_and_hosting.md` | Keep | |
| 16 | What does the overdue job do? | `mark_overdue_and_inactive`: a Due payment past its date becomes Over due, and a plan payment Over due for 7 days makes its subscription Inactive. It is safe to run again. | `app/billing/service.py`, `wiki/Payments_and_invoices.md`, `wiki/Subscriptions.md` | Keep | |
| 17 | When does the backend create the next plan payment? | `generate_due_payments` creates each plan payment 7 days before the renewal date, Due by the renewal date. | `app/billing/service.py`, `wiki/Payments_and_invoices.md`, `wiki/Subscriptions.md` | Keep | |
| 18 | What happens to an add-on payment when its service is completed? | `add_on_service_completed` sets a Due add-on payment to Over due at once and records a payment event "Service completed, payment not received". The scheduling service calls it when the visit's add-on is completed. | `app/billing/service.py`, `app/scheduling/service.py`, `wiki/Payments_and_invoices.md`, `wiki/Add_on_services.md` | Keep | |
| 19 | What shape does an API error have? | One envelope (`ErrorBody`): `code`, `message`, `fields` (per-field errors) and `request_id`. | `app/platform/errors.py` | Keep | |
| 20 | What does `/v1/public/config` return, and what is the latest migration? | Config returns `min_app_version` and `environment`. The latest migration is `20261030_0042_mani_foundation`, after `0041_plan_vehicle_category`. | `app/system/router.py`, `migrations/versions/`, `wiki/API_and_data_model.md` | Drop | |
