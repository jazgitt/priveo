# Scheduler rules v1.2: implementation plan and test plan

**Status:** Draft v0.1, 06-Nov-26. Plan only: no code, no migration, nothing merged. Building starts only after the owner approves this plan and names the first phase.
**Inputs:** `docs/reqs/scheduler-requirements.md` (133 SCHR- rows, v0.3), `docs/reqs/scheduler-gap-analysis.md` (G01 to G32, v0.3), CLAUDE.md merge rules, `tools/dev/check-local.sh`, `docs/build-and-release.md`.
**Facts checked in this work tree (`main` at migration head 0050):** the API tests are in `services/api/tests/` and the scheduler tests in `services/api/tests/scheduling/` (`test_solver.py`, `test_site_off_days.py`, `test_multi_slot_hours.py`, `test_scheduling_api.py`, `test_automatic_planning.py`, `test_rules.py`, `test_queue.py`, `test_partial_outcomes.py` and others; shared fixtures in `tests/scheduling/conftest.py`: `World`, `world`, `api`, `admin`, `run_week`). Pure solver tests build `SolverCrew` and `SolverJob` objects and call `solve_day` (`tests/scheduling/test_solver.py`). The migration test is `tests/test_migrations.py`. PostgreSQL runs through `services/api/scripts/test_postgres.py`. Web unit tests are vitest (`npm test`), browser tests are Playwright in `apps/web/e2e/` (`schedule.spec.ts`, `settings.spec.ts`, `crew.spec.ts`). `hypothesis` is not a dev dependency (`services/api/pyproject.toml:22`).

---

## 1. Principles and gates

1. **Serial, small pull requests.** One phase at a time, one slice (PR) at a time, in the order of section 3. A code PR is opened regular, a docs-only PR as a draft (CLAUDE.md, memory of 3-Nov-26). The owner confirms before each next phase.
2. **Local checks first.** Before marking a PR ready: `tools/dev/check-local.sh --changed`. The PostgreSQL stage is included for any API, database or scheduler change (never `--no-pg` for those). Merge only when the local checks and the four CI checks (`api-ci`, `web-ci`, `mobile-ci`, `web-e2e`) are green. A merge to `main` deploys to test (`docs/build-and-release.md`). Repeat runs rerun only the touched tests and say why.
3. **Migration number re-checked at build time.** The head on `main` is 0050 today. `check-local.sh` stops on a duplicate revision or more than one head. Each phase below says "0051 or the next free number".
4. **Kill switch.** A per-site setting `scheduler.rules_version` (site scope, stored in the new site settings store of P1a). Value 1 is the old behaviour and is the default for every existing site. Value 2 turns on the v1.2 rules built so far. A phase ships dark: its new code paths run only when the site's value is 2, and its migrations and settings are additive. The owner flips the value per site (gate OG7). Setting it back to 1 is the rollback for behaviour. The switch itself is a registry/site key editable in the portal, not a code constant (SCHR-CFG-01).
5. **Nothing hardcoded (SCHR-CFG).** Every new value is a registry key or a table row seeded by migration or the seed tool. Removing a constant must be behaviour-neutral: the migration seeds the value the code had (for example durations 20, 20 and 120, slots 05:00 to 11:00 on all days) for existing sites. The new defaults (30 minutes, Wednesday closed) are seeded for new sites and reach existing sites only through an approved data script (gates OG3 to OG5).
6. **Reuse before new** (SCHR-CFG-02, SCHR-CFG-10). Reuse the Settings page Schedule tab (every `schedule.*` and new `scheduler.*` registry key appears there by itself, `apps/web/src/pages/settings/SettingsPage.tsx`), the Slots, Services and Zones tabs (`apps/web/src/pages/reference/`) and Crew detail (`apps/web/src/pages/crew/`). New UI only: a "Scheduling rules" tab in Site Setup, a break dialog, and crew fields.
7. **API contract.** After any API change: `scripts/export_openapi.py` (`check-local.sh` regenerates and fails if stale) and, for mobile, `cd apps/mobile && dart run tool/gen_api.dart`. Commit the regenerated files.
8. **Do not decide for the owner.** Every open choice is a gate in the table below.

**Owner approval gates**

| Gate | What needs the owner | Needed before |
|---|---|---|
| OG1 | Approve this plan; say which phase goes first | Any build |
| OG2 | PR #156 (requirements and this plan) merged to `main`, so the SCHR- IDs exist there | P1a |
| OG3 | Wednesday closed on **live** sites: a data script for `working_slots` and for crew `working_hours` | Flipping any live site |
| OG4 | Durations 20 to 30 on **live** sites (services, and the two extra add-ons seeded at 20) | Flipping any live site |
| OG5 | Frozen or draft schedules that already hold Wednesday jobs: leave them or move them | OG3 |
| OG6 | Entitlement backfill: create the current week's entitlement for Active interior subscriptions; no past debt is created | P5 go-live |
| OG7 | Flip `scheduler.rules_version` to 2, per site, first on test, then each production site | Each flip |
| OG8 | Capacity decision (more cleaners, longer shifts, fewer cars per cleaner) after the capacity check of section 4 | Flipping a production site |
| OG9 | Production release: `v*` tag or manual run, with the reviewer approval of the `production` environment | Any production deploy |
| OG10 | Add `hypothesis` as a dev dependency for property tests, or keep plain seeded pytest loops (this plan assumes the latter) | P3 |
| OG11 | Customer wording changes (PAY-02, ONB-18, SUB-08) and the edits to existing requirement rows | P8 |

---

## 2. Phase plan

For every phase: **Contract** means export the OpenAPI file and run `dart run tool/gen_api.dart` if any response or request changed. **Rollback** always includes setting `scheduler.rules_version` back to 1 for the site, plus the item given. Migration downgrades are written by hand (CLAUDE.md) and tested (section 5).

### P1a. Site settings store and the end of rule constants
- **Goal:** one place for per-site values, a lookup layer, audit, and the kill switch; constants in `rules.py` removed. No behaviour change.
- **Covers:** SCHR-CFG-01 to 10, SCHR-PAR-01, SCHR-PAR-14, G25, G32, part of G27; hardcoded list items in gap analysis section 3a for `rules.py`, `automatic.py`.
- **PR slices**
  1. Migration `society_settings (society_id, key, value, updated_at, updated_by)` with unique (society, key); lookup functions in `app/directory/lookup.py` (site value, then global, then error if missing); tests.
  2. Registry keys in `directory/settings_registry.py` (`scheduler.rules_version` default 1, `scheduler.grid_minutes`, `scheduler.solve_seconds`, `scheduler.seed`, `scheduler.workers`, automatic retry minutes) seeded by migration; `scheduling/rules.py:12-15` and `automatic.py:59,87` read them; the guard test of section 5.
  3. Site settings API (`/v1/admin/directory/...`, audit through `DirectoryAudit` with `society_id`, `directory/models.py:172-187`) and the "Scheduling rules" tab skeleton in `apps/web/src/pages/reference/`.
- **Files:** `app/directory/{models,lookup,settings_registry,router,schemas,audit_scope}.py`, `app/scheduling/{rules,automatic}.py`, new migration, `apps/web/src/pages/reference/ReferencePage.tsx` and a new tab file, tests.
- **Config and UI:** new keys above on the Settings page Schedule tab (reuse); per-site values in the new tab.
- **Acceptance:** all existing scheduling tests pass unchanged; the changed settings are audited; a missing value stops a run with an alert (SCHR-CFG-04); the constants named in section 3a for these files are gone.
- **Rollback:** the migration downgrade drops the table; nothing reads it with version 1.

### P1b. Durations, weekly off, reporting and first-job time, Interior earliest
- **Goal:** the parameter rules that need no solver redesign.
- **Covers:** SCHR-PAR-02 to 08, 16; SCHR-HARD-04, 05, 06, 07; SCHR-EXT-02; G01 to G05, G13, G28, G29 (part), part of G27.
- **PR slices**
  1. Durations: remove `DURATIONS` from `scheduling/models.py:24` and `directory/defaults.py:9`; seed through migration and `seed.py` (existing sites keep 20, new sites 30); a re-run refreshes `duration_minutes` of unfrozen Scheduled jobs (`service.py:652-653`).
  2. Weekly off: `availability()` and `capacity()` return nothing on a day the site is closed for all cleaning services; the seed default leaves out the weekly-off weekday (`directory/seed.py:25-30`, `defaults.py:14-19`); the Slots tab shows it.
  3. Reporting and first-job time: migration for `scheduling_crew.reporting_minute` and `first_job_minute` (nullable); site defaults in the new tab; `availability()` applies the later of first-job time and window start; HoursEditor fields.
  4. Interior earliest: `service_windows()` (`service.py:575-580`) returns `max(slot start, setting)` for Cleaning-Internal; hand moves use the same function.
- **Files:** `app/scheduling/{service,models,rules}.py`, `app/directory/{defaults,seed,lookup}.py`, `app/crew/service.py`, `apps/web/src/pages/{reference,crew,schedule}/`, migrations, tests, capacity text (ADM-CAP-01 wording is P8).
- **Acceptance:** with the site at version 2, no job on the weekly-off day, none before the first-job time, no Interior before 07:00 on any day, jobs of 30 minutes; with version 1 the old plans are identical (regression run, section 5).
- **Rollback:** version 1; data scripts are reversible (the script prints the old values).

### P2. Hard weekday cutoff, weekend flexible, structured reasons and shortfall
- **Goal:** SCHR-CUT and SCHR-WKE, and reportable unassigned jobs.
- **Covers:** SCHR-HARD-08, 09, 13; SCHR-CUT-01 to 08; SCHR-WKE-01 to 06; SCHR-EXT-04; SCHR-OUT-04 (reason codes); SCHR-HIER-08; G07, G08, G14, G28.
- **PR slices**
  1. Keys `site.weekday_cutoff_hard`, `site.weekend_cutoff_flexible`, `site.weekend_weekdays`; `SolverJob` gets a hard end limit for strict days (`windows` argument); unplaced reason codes.
  2. Weekend soft penalty kept; weekend flag; lateness counted.
  3. Shortfall (cars and minutes) in the run summary and the Unscheduled and Needs scheduling lists.
  4. Hand moves: warn and flag instead of refusing (owner decision 10); breach recorded for the exception report.
- **Files:** `scheduling/{solver,service,schemas,router}.py`, web `schedule/` (warning and reasons), tests.
- **Contract:** yes (new reason and shortfall fields).
- **Acceptance:** on a strict day no job ends after its cutoff; a car whose cutoff cannot be met is Unscheduled with the reason "Customer cutoff" and counted in the shortfall; weekend lateness allowed and flagged; the scheduler itself never breaks a hard constraint.
- **Rollback:** version 1 restores the soft cutoff.

### P3. Two passes, ordered objectives, usable early capacity, solver parameters from settings
- **Goal:** the core solver change (SCHR-HIER, SCHR-EXT, SCHR-INT-07 to 09).
- **Covers:** SCHR-HIER-01 to 07, SCHR-EXT-01 to 10, SCHR-INT-07, 08, 09, SCHR-CFG-08; G17, G18, G21, G23.
- **PR slices**
  1. `STEP`, time limit, seed and workers read from settings (`solver.py:14, 50, 139-140`); behaviour-neutral.
  2. Split `solver_jobs` by service: solve Exteriors, pass the placements as `fixed`, solve Interiors in the gaps (`service.py:720`); Interior demand is still weekday-driven until P5.
  3. Ordered objectives and weights from configuration (`scheduler.objective_order`, `scheduler.weight_*`); tests per level.
  4. Usable-early-capacity term replaces the global early-start term (SCHR-EXT-05, G18).
  5. Run configuration snapshot stored with the run (migration: `schedule_run_config`, SCHR-CFG-08).
- **Acceptance:** scenario matrix rows S08 to S16 pass; determinism test passes; solve time within the budget of section 5.
- **Rollback:** version 1 uses the single-pass path (kept until P8 removes it).

### P4. Break
- **Covers:** SCHR-PAR-09, SCHR-BRK-01 to 10, SCHR-HIER-05 (break part); G06, G29.
- **PR slices**
  1. Migration `break_rules (id, society_id, crew_id null, start_date, end_date, start_minute, end_minute, enabled)`; site default keys; lookup `break_for(crew, day)` with the order date and crew, date, crew, site.
  2. Solver: break as a soft block in Pass A and a hard block in Pass B; missed-break flag stored per run result.
  3. Break dialog (Today, Tomorrow, Date range) on Site Setup and Crew detail.
  4. Capacity minus break; Board block; crew day.
- **Contract:** yes. **Acceptance:** scenario rows S17 to S20. **Rollback:** version 1; the downgrade drops `break_rules`.

### P5. Entitlement ledger, service week, FIFO, carry-forward, Deferred
- **Covers:** SCHR-PAR-12, 13; SCHR-HARD-10, 11; SCHR-INT-01 to 26; SCHR-DEF-01 to 06; SCHR-WKE-05; G09 to G12, G19, G31.
- **PR slices**
  1. Migration `interior_entitlements` and `jobs.service_week_start`; keys `schedule.interior_entitlement_per_week`, `schedule.service_week_start`; repeatable `ensure_entitlements` (SCHR-INT-19, 20).
  2. Interior demand from pending entitlements instead of the weekday (`service.py:151`), gated by version 2; one per week and one per car per day.
  3. FIFO ordering in Pass B, carry-forward and credit to the original week on completion (outcomes).
  4. Waiver for a fully paused week; one-day skip stays pending (SCHR-INT-21); the Deferred state for key or car unavailable; partial completion keeps ADM-CNC-10.
  5. Customer calendar projection (`changes/projection.py:18-29`).
  6. Backfill script (gate OG6), run on test first.
- **Contract:** yes (job and customer calendar fields; mobile generation needed). **Acceptance:** the catch-up example of requirements section 12 passes end to end. **Rollback:** version 1 ignores the ledger; the downgrade drops the table and the column.

### P6. Home zone and spill
- **Covers:** SCHR-ZONE-01 to 11; G16.
- **PR slices:** (1) migration `scheduling_crew.home_zone_id`, Crew detail picker, Trainee follows the Member; (2) solver terms: home zone first, spill into spare capacity, zone-switch penalty; (3) `jobs.cross_zone_reason` recorded and shown on the Board and crew day.
- **Contract:** yes. **Acceptance:** scenario rows S21 to S24. **Rollback:** version 1; downgrade drops the column.

### P7. Outputs
- **Covers:** SCHR-OUT-01 to 07; G24, G29.
- **PR slices:** (1) daily cleaner view endpoint; (2) weekly summary endpoint (grouped by original service week, overdue days, completion date); (3) exception report endpoint; (4) Reports tab on the Schedule page; (5) run summary and schedule history; (6) optional export (SCHR-OUT-06).
- **Contract:** yes. **Acceptance:** each report matches a hand-computed fixture week. **Rollback:** read-only endpoints; hide the tab.

### P8. Documentation follow-up
- **Covers:** gap analysis section 5 in full; G30.
- **PR slices:** (1) edit the existing requirement rows (gate OG11) and the version lines, check IDs with `/ids` and `/synccheck`; (2) `docs/coverage/business-rules.md`, `data-entities.md`; (3) wiki pages and `wiki/validate.py`; README prototype differences; board redesign doc; (4) add the scheduler file to the `REQS` list in `tools/priveo-reqs/hooks/register.ts`; (5) remove the version-1 path if the owner agrees.
- **Rollback:** documents only.

---

## 3. Dependency graph and PR order

P1a, then P1b, then P2, then P3, then P5. P4 (break) needs P3 and may run before or after P5. P6 needs P3 and, because it touches the same solver, runs serially after P5. P7 last. P8 starts after OG1 for the requirement-file edits and finishes last.

| Order | Phase | Can be released alone (dark) | Depends on |
|---|---|---|---|
| 1 | P1a | Yes | OG2 |
| 2 | P1b | Yes | P1a, OG3, OG4 for live sites |
| 3 | P2 | Yes | P1b |
| 4 | P3 | Yes | P2 |
| 5 | P4 | Yes | P3 |
| 6 | P5 | Yes | P3, OG6 |
| 7 | P6 | Yes | P5 |
| 8 | P7 | Yes | P5, P6 |
| 9 | P8 | Docs | OG11 |

---

## 4. Data and rollout plan

| Item | How | Gate |
|---|---|---|
| New settings and tables | Migration, additive, seeded with values equal to today's code for existing sites | none (dark) |
| New sites | Seed tool gives the new defaults (30 minutes, weekly off Wednesday, 05:00, 05:30, 07:00, break 09:30 to 10:00) | none |
| Existing sites' slots and crew hours (Wednesday) | A reviewed data script, run on test first, prints old and new values | OG3, OG5 |
| Existing durations and the two extra add-ons | Same kind of script | OG4 |
| Jobs already created at 20 minutes | Keep their length; unfrozen ones refresh on the next re-run | none |
| Frozen schedules that hold Wednesday jobs | Leave, or move by hand | OG5 |
| Entitlement backfill | Current week only, no past debt; test first | OG6 |
| Capacity check before any flip | Run the capacity view for the next 4 weeks at version 2 in a copy: expect about 10 jobs per cleaner per day against 18 today, and no Interior before a 09:00 cutoff on strict days (gap analysis section 7) | OG8 |
| Flip | `scheduler.rules_version` = 2 per site, test site first | OG7 |
| Production | Merge to `main` deploys to test. Production deploys from a `v*` tag or a manual run and the `production` GitHub Environment reviewer; a migration runs before the new code and must keep the previous release working (`docs/build-and-release.md`) | OG9 |

A site never changes behaviour because of a deploy; it changes only when its value is flipped.

---

## 5. Test plan

### 5.1 Levels and commands

| Level | Where | Command |
|---|---|---|
| Solver unit (pure function) | `services/api/tests/scheduling/test_solver.py` and new `test_rules_v2_*.py` | `cd services/api && .venv/bin/python -m pytest -q tests/scheduling` |
| API (SQLite) | `services/api/tests/scheduling/` using `world`, `api`, `admin`, `run_week` | `tools/dev/check-local.sh --only api` |
| API on PostgreSQL | same tests on a disposable cluster | `tools/dev/check-local.sh --only pg` (runs `services/api/scripts/test_postgres.py`) |
| Migrations | `services/api/tests/test_migrations.py` and one file per migration | in the api and pg stages |
| Web unit | `apps/web/src/pages/**/*.test.tsx` (vitest) | `cd apps/web && npm run lint && npm test && npm run build` |
| Browser | `apps/web/e2e/schedule.spec.ts`, `settings.spec.ts`, `crew.spec.ts` (Playwright) | `tools/dev/check-local.sh --e2e` |
| Mobile (only when the contract changes) | `apps/mobile/test` | `cd apps/mobile && flutter analyze && flutter test` |
| Everything touched | | `tools/dev/check-local.sh --changed` before every PR, PostgreSQL included for API and scheduler changes |

The golden-image tests run on Linux only and stay in CI.

### 5.2 Traceability by group

Every SCHR group has a test file. The convention: each test name starts with the row ID (`test_schr_hard_08_...`) so a search finds it. Row counts are of the requirements file v0.3.

| Group | Rows | Owner rows | Phase | Test file | Level |
|---|---|---|---|---|---|
| SCHR-PAR | 16 | 11 | P1a/P1b | `tests/scheduling/test_rules_v2_settings.py` | API |
| SCHR-CFG | 10 | 8 | P1a | `tests/scheduling/test_rules_v2_config_guard.py` | API |
| SCHR-HIER | 8 | 5 | P3 | `tests/scheduling/test_rules_v2_hierarchy.py` | Solver |
| SCHR-HARD | 13 | 11 | P1b/P2 | `tests/scheduling/test_rules_v2_hard.py` | Solver + property |
| SCHR-EXT | 12 | 10 | P3 | `tests/scheduling/test_rules_v2_exterior.py` | Solver |
| SCHR-INT | 26 | 21 | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | Solver + API |
| SCHR-CUT | 8 | 6 | P2 | `tests/scheduling/test_rules_v2_cutoff.py` | Solver + API |
| SCHR-WKE | 6 | 5 | P2 | `tests/scheduling/test_rules_v2_cutoff.py` | Solver |
| SCHR-ZONE | 11 | 7 | P6 | `tests/scheduling/test_rules_v2_zones.py` | Solver + API |
| SCHR-BRK | 10 | 6 | P4 | `tests/scheduling/test_rules_v2_break.py` | Solver + API |
| SCHR-OUT | 7 | 3 | P7 | `tests/scheduling/test_rules_v2_reports.py` | API + web |
| SCHR-DEF | 6 | 5 | P5 | `tests/scheduling/test_rules_v2_deferral.py` | API |

Existing files that also carry assertions: `test_solver.py`, `test_site_off_days.py`, `test_multi_slot_hours.py`, `test_scheduling_api.py`, `test_automatic_planning.py`, `test_partial_outcomes.py`, `test_queue.py`, `test_rules.py`. Derived rows are covered by the same group file (one test each where the behaviour is checkable).

### 5.3 Traceability for every row whose status contains Owner (98 rows)

Test names are the planned names; the full name is fixed when the test is written.

| Row | Status | Phase | Test file | Planned test | Level |
|---|---|---|---|---|---|
| SCHR-PAR-02 | Owner | P1a/P1b | `tests/scheduling/test_rules_v2_settings.py` | `test_schr_par_02_working_days_are_monday_tuesday_thursday` | API |
| SCHR-PAR-03 | Owner | P1a/P1b | `tests/scheduling/test_rules_v2_settings.py` | `test_schr_par_03_the_weekly_off_weekday_is_a` | API |
| SCHR-PAR-04 | Owner | P1a/P1b | `tests/scheduling/test_rules_v2_settings.py` | `test_schr_par_04_cleaners_report_at_05_00_and` | API |
| SCHR-PAR-06 | Owner | P1a/P1b | `tests/scheduling/test_rules_v2_settings.py` | `test_schr_par_06_the_job_duration_is_30_minutes` | API |
| SCHR-PAR-08 | Owner | P1a/P1b | `tests/scheduling/test_rules_v2_settings.py` | `test_schr_par_08_the_earliest_start_of_an_interior` | API |
| SCHR-PAR-09 | Owner | P1a/P1b | `tests/scheduling/test_rules_v2_settings.py` | `test_schr_par_09_the_break_for_all_crew_is` | API |
| SCHR-PAR-11 | Owner | P1a/P1b | `tests/scheduling/test_rules_v2_settings.py` | `test_schr_par_11_the_customer_cutoff_has_two_settings` | API |
| SCHR-PAR-12 | Owner | P1a/P1b | `tests/scheduling/test_rules_v2_settings.py` | `test_schr_par_12_the_interior_entitlement_is_one_interior` | API |
| SCHR-PAR-13 | Owner | P1a/P1b | `tests/scheduling/test_rules_v2_settings.py` | `test_schr_par_13_a_service_week_runs_monday_to` | API |
| SCHR-PAR-15 | Owner | P1a/P1b | `tests/scheduling/test_rules_v2_settings.py` | `test_schr_par_15_the_order_and_weights_of_the` | API |
| SCHR-PAR-16 | Owner | P1a/P1b | `tests/scheduling/test_rules_v2_settings.py` | `test_schr_par_16_the_weekly_off_applies_to_exterior` | API |
| SCHR-CFG-01 | Owner | P1a | `tests/scheduling/test_rules_v2_config_guard.py` | `test_schr_cfg_01_no_rule_configuration_or_value_is` | API |
| SCHR-CFG-02 | Owner | P1a | `tests/scheduling/test_rules_v2_config_guard.py` | `test_schr_cfg_02_every_value_is_editable_by_the` | API |
| SCHR-CFG-03 | Owner | P1a | `tests/scheduling/test_rules_v2_config_guard.py` | `test_schr_cfg_03_defaults_are_seeded_by_migration_or` | API |
| SCHR-CFG-04 | Owner and Derived | P1a | `tests/scheduling/test_rules_v2_config_guard.py` | `test_schr_cfg_04_the_solver_and_the_planner_read` | API |
| SCHR-CFG-05 | Owner and Derived | P1a | `tests/scheduling/test_rules_v2_config_guard.py` | `test_schr_cfg_05_every_value_is_validated_on_save` | API |
| SCHR-CFG-06 | Owner | P1a | `tests/scheduling/test_rules_v2_config_guard.py` | `test_schr_cfg_06_every_change_is_recorded_in_the` | API |
| SCHR-CFG-07 | Owner | P1a | `tests/scheduling/test_rules_v2_config_guard.py` | `test_schr_cfg_07_a_change_applies_from_the_next` | API |
| SCHR-CFG-09 | Owner and Derived | P1a | `tests/scheduling/test_rules_v2_config_guard.py` | `test_schr_cfg_09_the_existing_constants_listed_in_hardcoded` | API |
| SCHR-HIER-02 | Owner | P3 | `tests/scheduling/test_rules_v2_hierarchy.py` | `test_schr_hier_02_hard_constraints_are_never_broken_by` | Solver |
| SCHR-HIER-04 | Owner | P3 | `tests/scheduling/test_rules_v2_hierarchy.py` | `test_schr_hier_04_the_priority_order_in_the_sheet` | Solver |
| SCHR-HIER-05 | Owner and Derived | P3 | `tests/scheduling/test_rules_v2_hierarchy.py` | `test_schr_hier_05_where_the_sheet_s_list_puts` | Solver |
| SCHR-HIER-07 | Owner | P3 | `tests/scheduling/test_rules_v2_hierarchy.py` | `test_schr_hier_07_pass_a_and_pass_b_are` | Solver |
| SCHR-HIER-08 | Owner | P3 | `tests/scheduling/test_rules_v2_hierarchy.py` | `test_schr_hier_08_jobs_placed_by_hand_and_jobs` | Solver |
| SCHR-HARD-01 | Owner | P1b/P2 | `tests/scheduling/test_rules_v2_hard.py` | `test_schr_hard_01_before_assigning_the_scheduler_checks_each` | Solver + property |
| SCHR-HARD-02 | Owner | P1b/P2 | `tests/scheduling/test_rules_v2_hard.py` | `test_schr_hard_02_a_cleaner_s_own_shift_end` | Solver + property |
| SCHR-HARD-03 | Owner | P1b/P2 | `tests/scheduling/test_rules_v2_hard.py` | `test_schr_hard_03_a_cleaner_is_never_given_two` | Solver + property |
| SCHR-HARD-04 | Owner | P1b/P2 | `tests/scheduling/test_rules_v2_hard.py` | `test_schr_hard_04_no_job_starts_before_the_cleaner` | Solver + property |
| SCHR-HARD-05 | Owner | P1b/P2 | `tests/scheduling/test_rules_v2_hard.py` | `test_schr_hard_05_no_interior_starts_before_the_interior` | Solver + property |
| SCHR-HARD-06 | Owner | P1b/P2 | `tests/scheduling/test_rules_v2_hard.py` | `test_schr_hard_06_every_exterior_and_every_interior_takes` | Solver + property |
| SCHR-HARD-07 | Owner | P1b/P2 | `tests/scheduling/test_rules_v2_hard.py` | `test_schr_hard_07_no_exterior_or_interior_is_planned` | Solver + property |
| SCHR-HARD-08 | Owner | P1b/P2 | `tests/scheduling/test_rules_v2_hard.py` | `test_schr_hard_08_on_a_strict_day_monday_tuesday` | Solver + property |
| SCHR-HARD-09 | Owner | P1b/P2 | `tests/scheduling/test_rules_v2_hard.py` | `test_schr_hard_09_every_active_car_needs_one_exterior` | Solver + property |
| SCHR-HARD-10 | Owner | P1b/P2 | `tests/scheduling/test_rules_v2_hard.py` | `test_schr_hard_10_at_most_one_interior_is_planned` | Solver + property |
| SCHR-HARD-11 | Owner | P1b/P2 | `tests/scheduling/test_rules_v2_hard.py` | `test_schr_hard_11_at_most_one_interior_is_planned` | Solver + property |
| SCHR-EXT-01 | Owner | P3 | `tests/scheduling/test_rules_v2_exterior.py` | `test_schr_ext_01_every_active_car_has_one_exterior` | Solver |
| SCHR-EXT-02 | Owner | P3 | `tests/scheduling/test_rules_v2_exterior.py` | `test_schr_ext_02_each_exterior_takes_a_fixed_30` | Solver |
| SCHR-EXT-03 | Owner | P3 | `tests/scheduling/test_rules_v2_exterior.py` | `test_schr_ext_03_all_exterior_jobs_of_the_day` | Solver |
| SCHR-EXT-04 | Owner | P3 | `tests/scheduling/test_rules_v2_exterior.py` | `test_schr_ext_04_exterior_has_the_highest_service_priority` | Solver |
| SCHR-EXT-05 | Owner and Derived | P3 | `tests/scheduling/test_rules_v2_exterior.py` | `test_schr_ext_05_among_plans_that_cover_the_same` | Solver |
| SCHR-EXT-06 | Owner | P3 | `tests/scheduling/test_rules_v2_exterior.py` | `test_schr_ext_06_early_free_capacity_is_never_made` | Solver |
| SCHR-EXT-07 | Owner | P3 | `tests/scheduling/test_rules_v2_exterior.py` | `test_schr_ext_07_a_free_slot_is_never_kept` | Solver |
| SCHR-EXT-08 | Owner | P3 | `tests/scheduling/test_rules_v2_exterior.py` | `test_schr_ext_08_the_time_between_the_first_job` | Solver |
| SCHR-EXT-10 | Owner | P3 | `tests/scheduling/test_rules_v2_exterior.py` | `test_schr_ext_10_the_exterior_pass_minimises_zone_changes` | Solver |
| SCHR-EXT-11 | Owner and Derived | P3 | `tests/scheduling/test_rules_v2_exterior.py` | `test_schr_ext_11_a_subscription_with_a_weekly_or` | Solver |
| SCHR-INT-01 | Owner and Derived | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_01_an_interior_is_planned_for_a` | Solver + API |
| SCHR-INT-02 | Owner | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_02_each_interior_takes_exactly_30_minutes` | Solver + API |
| SCHR-INT-03 | Owner | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_03_no_interior_starts_before_07_00` | Solver + API |
| SCHR-INT-04 | Owner | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_04_a_visit_that_has_both_an` | Solver + API |
| SCHR-INT-05 | Owner and Derived | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_05_the_customer_s_interior_care_day` | Solver + API |
| SCHR-INT-06 | Owner | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_06_the_default_entitlement_is_one_interior` | Solver + API |
| SCHR-INT-07 | Owner | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_07_pass_b_starts_only_after_all` | Solver + API |
| SCHR-INT-08 | Owner | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_08_exterior_first_is_a_planning_sequence` | Solver + API |
| SCHR-INT-09 | Owner | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_09_pass_b_respects_weekday_cutoffs_kept` | Solver + API |
| SCHR-INT-10 | Owner | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_10_the_scheduler_places_as_many_weekday` | Solver + API |
| SCHR-INT-11 | Owner | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_11_every_interior_carries_an_explicit_service` | Solver + API |
| SCHR-INT-12 | Owner and Derived | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_12_pass_b_orders_eligible_entitlements_by` | Solver + API |
| SCHR-INT-13 | Owner | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_13_if_the_interior_of_week_1` | Solver + API |
| SCHR-INT-14 | Owner | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_14_when_the_overdue_interior_is_done` | Solver + API |
| SCHR-INT-15 | Owner | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_15_week_2_s_entitlement_is_never` | Solver + API |
| SCHR-INT-16 | Owner | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_16_an_overdue_interior_keeps_its_original` | Solver + API |
| SCHR-INT-17 | Owner | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_17_reports_show_for_each_interior_the` | Solver + API |
| SCHR-INT-18 | Owner | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_18_more_than_one_physical_interior_may` | Solver + API |
| SCHR-INT-20 | Owner and Derived | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_20_every_service_week_that_a_subscription` | Solver + API |
| SCHR-INT-21 | Owner | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_21_an_operational_miss_car_keys_capacity` | Solver + API |
| SCHR-INT-25 | Owner | P5 | `tests/scheduling/test_rules_v2_entitlement.py` | `test_schr_int_25_the_entitlement_model_replaces_the_custom` | Solver + API |
| SCHR-CUT-01 | Owner | P2 | `tests/scheduling/test_rules_v2_cutoff.py` | `test_schr_cut_01_on_monday_tuesday_thursday_and_friday` | Solver + API |
| SCHR-CUT-02 | Owner | P2 | `tests/scheduling/test_rules_v2_cutoff.py` | `test_schr_cut_02_a_job_is_never_scheduled_to` | Solver + API |
| SCHR-CUT-03 | Owner | P2 | `tests/scheduling/test_rules_v2_cutoff.py` | `test_schr_cut_03_if_an_interior_cannot_fit_before` | Solver + API |
| SCHR-CUT-04 | Owner | P2 | `tests/scheduling/test_rules_v2_cutoff.py` | `test_schr_cut_04_if_an_exterior_cannot_fit_before` | Solver + API |
| SCHR-CUT-05 | Owner | P2 | `tests/scheduling/test_rules_v2_cutoff.py` | `test_schr_cut_05_an_admin_who_places_a_job` | Solver + API |
| SCHR-CUT-06 | Owner | P2 | `tests/scheduling/test_rules_v2_cutoff.py` | `test_schr_cut_06_the_three_cutoffs_are_named_in` | Solver + API |
| SCHR-WKE-01 | Owner | P2 | `tests/scheduling/test_rules_v2_cutoff.py` | `test_schr_wke_01_on_saturday_and_sunday_the_service` | Solver |
| SCHR-WKE-02 | Owner | P2 | `tests/scheduling/test_rules_v2_cutoff.py` | `test_schr_wke_02_the_scheduler_finishes_all_weekend_exteriors` | Solver |
| SCHR-WKE-03 | Owner | P2 | `tests/scheduling/test_rules_v2_cutoff.py` | `test_schr_wke_03_a_weekend_exterior_or_interior_may` | Solver |
| SCHR-WKE-05 | Owner | P2 | `tests/scheduling/test_rules_v2_cutoff.py` | `test_schr_wke_05_eligible_outstanding_interiors_are_allocated_on` | Solver |
| SCHR-WKE-06 | Owner | P2 | `tests/scheduling/test_rules_v2_cutoff.py` | `test_schr_wke_06_weekend_lateness_against_a_cutoff_is` | Solver |
| SCHR-ZONE-01 | Owner | P6 | `tests/scheduling/test_rules_v2_zones.py` | `test_schr_zone_01_each_society_has_several_zones_and` | Solver + API |
| SCHR-ZONE-02 | Owner | P6 | `tests/scheduling/test_rules_v2_zones.py` | `test_schr_zone_02_the_scheduler_minimises_the_number_of` | Solver + API |
| SCHR-ZONE-03 | Owner | P6 | `tests/scheduling/test_rules_v2_zones.py` | `test_schr_zone_03_after_the_home_zone_jobs_are` | Solver + API |
| SCHR-ZONE-04 | Owner and Derived | P6 | `tests/scheduling/test_rules_v2_zones.py` | `test_schr_zone_04_before_a_cross_zone_assignment_the` | Solver + API |
| SCHR-ZONE-05 | Owner | P6 | `tests/scheduling/test_rules_v2_zones.py` | `test_schr_zone_05_movement_across_zones_is_part_of` | Solver + API |
| SCHR-ZONE-06 | Owner and Derived | P6 | `tests/scheduling/test_rules_v2_zones.py` | `test_schr_zone_06_the_reason_for_each_cross_zone` | Solver + API |
| SCHR-ZONE-07 | Owner and Derived | P6 | `tests/scheduling/test_rules_v2_zones.py` | `test_schr_zone_07_the_admin_sets_one_home_zone` | Solver + API |
| SCHR-BRK-01 | Owner | P4 | `tests/scheduling/test_rules_v2_break.py` | `test_schr_brk_01_the_scheduler_tries_to_give_each` | Solver + API |
| SCHR-BRK-02 | Owner | P4 | `tests/scheduling/test_rules_v2_break.py` | `test_schr_brk_02_if_the_break_conflicts_with_an` | Solver + API |
| SCHR-BRK-03 | Owner | P4 | `tests/scheduling/test_rules_v2_break.py` | `test_schr_brk_03_mandatory_exterior_coverage_and_hard_weekday` | Solver + API |
| SCHR-BRK-04 | Owner | P4 | `tests/scheduling/test_rules_v2_break.py` | `test_schr_brk_04_every_missed_break_is_flagged_in` | Solver + API |
| SCHR-BRK-05 | Owner | P4 | `tests/scheduling/test_rules_v2_break.py` | `test_schr_brk_05_the_admin_can_change_the_break` | Solver + API |
| SCHR-BRK-06 | Owner | P4 | `tests/scheduling/test_rules_v2_break.py` | `test_schr_brk_06_the_site_has_the_default_break` | Solver + API |
| SCHR-OUT-01 | Owner | P7 | `tests/scheduling/test_rules_v2_reports.py` | `test_schr_out_01_the_daily_cleaner_wise_view_shows` | API + web |
| SCHR-OUT-02 | Owner | P7 | `tests/scheduling/test_rules_v2_reports.py` | `test_schr_out_02_the_weekly_summary_shows_completed_against` | API + web |
| SCHR-OUT-03 | Owner | P7 | `tests/scheduling/test_rules_v2_reports.py` | `test_schr_out_03_the_exception_report_shows_unassigned_mandatory` | API + web |
| SCHR-DEF-01 | Owner | P5 | `tests/scheduling/test_rules_v2_deferral.py` | `test_schr_def_01_at_execution_if_the_car_or` | API |
| SCHR-DEF-02 | Owner | P5 | `tests/scheduling/test_rules_v2_deferral.py` | `test_schr_def_02_a_deferred_service_is_tried_again` | API |
| SCHR-DEF-04 | Owner | P5 | `tests/scheduling/test_rules_v2_deferral.py` | `test_schr_def_04_the_deferral_reasons_come_from_configuration` | API |
| SCHR-DEF-05 | Owner | P5 | `tests/scheduling/test_rules_v2_deferral.py` | `test_schr_def_05_both_by_case_when_the_key` | API |
| SCHR-DEF-06 | Owner | P5 | `tests/scheduling/test_rules_v2_deferral.py` | `test_schr_def_06_a_pending_interior_does_not_expire` | API |

### 5.4 Solver scenario matrix

Deterministic: fixed seed from the settings, small fixtures built as in `test_solver.py` (`SolverCrew`, `SolverJob`), plus API scenarios on `world`. Each is a golden expectation (placements and unassigned reasons).

| # | Scenario | Expected | Rows | Phase |
|---|---|---|---|---|
| S01 | Weekly-off weekday with cars and cleaners | No job at all; capacity shows 0 for the day | SCHR-HARD-07, PAR-02 | P1b |
| S02 | Cleaner window starts 05:00, first-job 05:30 | No job starts before 05:30 | SCHR-HARD-04 | P1b |
| S03 | Per-cleaner first-job override | Override wins over site value | SCHR-PAR-04 | P1b |
| S04 | Interior on a weekday and on a weekend with free time before 07:00 | No Interior starts before 07:00 | SCHR-HARD-05, INT-03 | P1b |
| S05 | Durations 30/30; one visit with both | 60 minutes of work, no travel added | SCHR-HARD-06, PAR-06, INT-04 | P1b |
| S06 | Weekday cutoff, Exterior and Interior | Neither ends after the cutoff; the impossible one is unassigned with a reason | SCHR-HARD-08, CUT-01 to 04 | P2 |
| S07 | Weekend cutoff | Job may end late; lateness reported; stays in shift | SCHR-WKE-01 to 03, 06 | P2 |
| S08 | All Exteriors fit with room to spare | All Exteriors placed before any Interior | SCHR-EXT-03, INT-07 | P3 |
| S09 | Capacity short for Exteriors | Maximum Exteriors placed; shortfall in cars and minutes | SCHR-EXT-04, HARD-09 | P3 |
| S10 | Cleaner done with Exteriors while another still works | Interior assigned to the free cleaner | SCHR-INT-08 | P3 |
| S11 | Same car, Exterior and Interior, two cleaners | No overlap on the car | SCHR-HARD-12, INT-04 | P3 |
| S12 | Early free capacity against idle slot | An eligible Interior takes the free slot | SCHR-EXT-07 | P3 |
| S13 | Two plans, same coverage | The plan with more usable early capacity wins | SCHR-EXT-05 | P3 |
| S14 | Objective order changed in configuration | Plan changes as the new order says | SCHR-PAR-15, CFG-01 | P3 |
| S15 | Trainee, absent cleaner, Late start, shift end | Trainee never assigned; absent excluded; job ends in shift | SCHR-HARD-01, 02 | P3 |
| S16 | Same input twice | Identical plan (determinism) | SCHR-HIER-06 | P3 |
| S17 | Break and an Interior conflict | Break kept, Interior deferred | SCHR-BRK-02 | P4 |
| S18 | Break and an Exterior conflict, no other plan | Exterior placed, missed break flagged | SCHR-BRK-03, 04 | P4 |
| S19 | Break and a weekday cutoff | Cutoff wins, break flagged | SCHR-BRK-03 | P4 |
| S20 | Weekend: break against cutoff | Break wins, Interior after it, flagged late | SCHR-HIER-05 | P4 |
| S21 | Home zone full, spare capacity elsewhere | Home zone first, then spill with reason | SCHR-ZONE-01, 03, 06 | P6 |
| S22 | Home-zone cleaner absent | Other cleaners take the zone, reason recorded | SCHR-ZONE-06, 07 | P6 |
| S23 | Cross-zone job would push a home job past cutoff | Not placed cross-zone | SCHR-ZONE-04 | P6 |
| S24 | Car with no zone; site with no home zones | No cross-zone record; plans as today | SCHR-ZONE-08, 11 | P6 |
| S25 | Three cars, week 1 Interior missed | Week 1 is done first in week 2 and credited to week 1 | SCHR-INT-13 to 17 | P5 |
| S26 | Catch-up example (requirements section 12) | Two Interiors in week 2's calendar week on separate days, one per service week | SCHR-INT-18, HARD-10, 11 | P5 |
| S27 | Two entitlements, capacity for one | Oldest service week placed (FIFO) | SCHR-INT-12 | P5 |
| S28 | Key unavailable at execution | Deferred with reason, returns to Pending, replanned; never Completed | SCHR-DEF-01 to 03 | P5 |
| S29 | Partial completion | ADM-CNC-10 next-day rule kept | SCHR-DEF-05 | P5 |
| S30 | Fully paused week; one-day skip | Paused week waived; skip leaves entitlement pending | SCHR-INT-21 | P5 |
| S31 | First week part-way through | The part week owes one Interior | SCHR-INT-20 | P5 |
| S32 | Extra Interior add-on or Deep Spa | Weekly entitlement not used | SCHR-INT-22 | P5 |
| S33 | Hand placement against a rule | Warning, allowed, breach in exception report | SCHR-HIER-08, CUT-05 | P2 |

### 5.5 Property tests

Plain pytest with seeded random generators (no new dependency; gate OG10 if `hypothesis` is wanted). Generate 200 random days (cleaners, windows, cars, cutoffs, entitlements) per run and check: no two jobs overlap for a cleaner or a car; every job inside a cleaner window; nothing before first-job time; no Interior before the Interior-earliest time; no job on the weekly-off day; on strict days no job ends after its cutoff; at most one Interior per car per service week and per day; Exterior count never decreases when capacity is added; same input gives the same output. File: `tests/scheduling/test_rules_v2_properties.py`.

### 5.6 Configuration guard tests (SCHR-CFG-09)

`tests/scheduling/test_rules_v2_config_guard.py`:
- A source scan fails if any listed constant (gap analysis section 3a: `STEP`, `_PLACED`, `_LATE`, `_EARLY`, `DURATIONS` in `scheduling/models.py` and `directory/defaults.py`, `FREEZE_HOUR`, `CUSTOMER_HOUR`, `UNFREEZE_CODE`, the `(300, 660)` fallback) reappears in `app/scheduling`, `app/crew` or `app/directory`.
- Every new registry key rejects out-of-range and malformed values with a message (SCHR-CFG-05).
- Saving a key writes an Audit row with old value, new value and site (SCHR-CFG-06).
- A change applies to the next unfrozen plan and leaves a frozen schedule and past reports unchanged (SCHR-CFG-07).
- A missing value stops the run with an alert, with no hidden default (SCHR-CFG-04).
- Each run stores the values it used (SCHR-CFG-08).
- Seeds: a fresh database has every key (SCHR-CFG-03).

### 5.7 Migration tests

Extend `tests/test_migrations.py` (tables built by the migrations match the models) and add one test per migration: upgrade and downgrade on SQLite and on PostgreSQL, seeded defaults present, existing-site values equal to the old code values, upgrade on a database holding old data. Run in the api and pg stages. The disposable PostgreSQL cluster is the only database used; `TEST_DATABASE_URL` is never an application database (CLAUDE.md).

### 5.8 Regression list for the 30-minute change

Expectations to review and update in P1b (listed in gap analysis section 7): `tests/scheduling/test_solver.py`, `test_site_off_days.py`, `test_multi_slot_hours.py`, `test_scheduling_api.py`, `test_automatic_planning.py`, `test_admin_job_ops.py`, `test_day_summary.py`; `tests/addons/test_addons.py`, `test_extra_addons.py`; `tests/directory/test_directory.py`; `tests/customer_reads/test_calendar_projection.py`; `tests/test_customer_scheduling_upgrade.py`; `tests/visits/conftest.py`; `tests/mani/test_tools_read.py`; web `apps/web/src/pages/schedule/Board.test.tsx` and `SchedulePage.test.tsx`; Playwright `apps/web/e2e/schedule.spec.ts`. Rule: with the site at version 1 the old expectations must still pass; the 30-minute expectations are added next to them, not instead.

### 5.9 Performance

Measure, do not assume:
- Solve time per site-day with two passes for 30, 60 and 120 cars and 4, 8 and 14 cleaners, against the per-pass limit from `scheduler.solve_seconds` (10 seconds today, `solver.py:50`). Worst case per day is two passes at the limit.
- A seven-day automatic run (`automatic.py`) for the seeded two societies and for a synthetic 10 sites, summed. The hosting function duration limit is not set in `services/api/vercel.json` and was not verified here; read it from the Vercel project before P3 is released. If the run can exceed it, plan days in separate invocations.
- A 30-day (Monthly) run, and a re-run with many hand-placed fixed jobs.
Budgets are written into the P3 PR description and stored as settings, not constants.

### 5.10 UAT on the test environment (`priveo-api-test`)

Prerequisite: the phase is merged and deployed to test; the test site flipped to version 2 (gate OG7) using `scripts/seed_two_societies.py` data. Script per phase:
1. Reset the two seeded societies; set the site values from the requirements defaults.
2. Run the week's plan from the Schedule page; open the Board for a strict day, a Wednesday, a Saturday and a Sunday.
3. Check against the phase's acceptance list (section 2) and the scenario rows of that phase, with the expected values written beforehand by the tester.
4. Hand-place a job against a rule; confirm the warning and the exception report entry.
5. Edit a setting; confirm the audit row and that the frozen schedule did not change.
6. Flip the site back to version 1; confirm the old plan returns.
7. Run `scripts/smoke_test.py` against the test API.
**Exit criteria:** every acceptance item passes; no open defect of severity high; the capacity check of section 4 is shown to the owner; the owner signs off the phase. Only then is a production release asked for (OG9).

### 5.11 Defect handling

A defect found in UAT or CI is recorded with the SCHR- or G ID, the scenario number and a failing test first. It is fixed in a small PR on the phase branch family. Bug counts and stages are kept in `docs/feature-status.json` through `/fstatus` (`bugs <ID> <n>`); a row moves Draft, In Dev, Unit Tested, Functional Tested, Security Test. A row does not move to Functional Tested while it has an open bug. Note: the three requirement files are tracked by the tool; the scheduler file is not until P8 adds it to `REQS`, so its rows are updated by hand until then.

---

## 6. Effort and sequence

| Phase | Size (gap analysis) | PR slices | Critical path |
|---|---|---|---|
| P1a | M | 3 | Yes |
| P1b | L (4 slices of S to M) | 4 | Yes |
| P2 | M | 4 | Yes |
| P3 | L | 5 | Yes |
| P4 | L | 4 | No |
| P5 | L | 6 | Yes |
| P6 | M | 3 | No |
| P7 | L | 5 to 6 | No |
| P8 | M | 5 | No |

Critical path: P1a, P1b, P2, P3, P5. Suggested order for the owner to confirm: P1a, P1b, P2, P3, P5, P4, P6, P7, P8. The owner decides the order and when each wave starts (OG1).

---

## 7. Risks and open items

- **Capacity** (gap analysis section 7): about 10 jobs per cleaner per day against 18 today, and no Interior before a 09:00 customer cutoff on strict days. Mitigation: the capacity check and gate OG8 before any production flip.
- **Solve time:** two passes double the solver calls and the hosting limit was not verified (section 5.9).
- **Backfill:** creates the current week's entitlement only (OG6); past weeks are not turned into debt.
- **Customer calendar wording:** Interior may land on a day other than the preferred day (SCHR-INT-05); the projection and the wording change in P5 and P8 (OG11).
- **Custom interior day** is replaced by the entitlement model (owner decision 8); the notes stay informational.
- **Tooling blind spot:** `tools/priveo-reqs` tracks only three requirement files until P8.
- **Reporting-time note** in the owner's sheet was truncated in extraction; it is read as "each crew member".
- **Not verified in this plan:** the hosting function duration limit; whether the `production` GitHub Environment currently has a required reviewer (the build document says it should); live site data (slots, durations, frozen Wednesday jobs); the Flutter day views.
