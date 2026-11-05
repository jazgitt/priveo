# Scheduler rules v1.2: implementation plan and test plan

**Build stories:** the work is divided into small independent stories, each with its own files, tests and pull request, in `docs/design/scheduler-build-stories.md`. This file keeps the principles, the owner gates OG1 to OG11, the kill switch and the test plan.
**Status:** Draft v0.2, 06-Nov-26 (phases now point to the stories). Plan only: no code, no migration, nothing merged. Building starts only after the owner approves this plan and names the first phase.
**Inputs:** `docs/reqs/scheduler-requirements.md` (133 SCHR- rows, v0.4), `docs/reqs/scheduler-gap-analysis.md` (G01 to G32, v0.3), CLAUDE.md merge rules, `tools/dev/check-local.sh`, `docs/build-and-release.md`.
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

The phase blocks of v0.1 are replaced by the build stories. Each story card has its goal, SCHR rows, gaps, write set, touch points, acceptance, tests, kill switch, rollback and size. The phases below only group them; the order of building and merging is in `scheduler-build-stories.md` sections 2 to 4.

| Phase | Content | Stories |
|---|---|---|
| P1a | Site settings store, lookup layer, kill switch, run snapshot, constants out of `rules.py` | SCHS-01, SCHS-02, SCHS-06, SCHS-07, SCHS-08, SCHS-09, SCHS-18, SCHS-52 |
| P1b | Durations, weekly off, reporting and first-job time, Interior earliest, crew fields | SCHS-10, SCHS-11, SCHS-12, SCHS-13, SCHS-14, SCHS-15, SCHS-16, SCHS-17 |
| P2 | Hard weekday cutoff, weekend flexible, structured reasons, hand-placement warning | SCHS-19, SCHS-20, SCHS-21, SCHS-22 |
| P3 | Solver modules, window seam, two passes, ordered objectives, early capacity, parameters from settings, benchmark | SCHS-03, SCHS-04, SCHS-05, SCHS-25, SCHS-32, SCHS-33, SCHS-42, SCHS-49, SCHS-58 |
| P4 | Break: store, dialog, solver, capacity, display | SCHS-23, SCHS-28, SCHS-34, SCHS-43, SCHS-35 |
| P5 | Entitlement ledger, ledger demand, FIFO, Deferred state, replanning, backfill | SCHS-24, SCHS-30, SCHS-31, SCHS-36, SCHS-37, SCHS-46, SCHS-47, SCHS-38, SCHS-51 |
| P6 | Home zone field, solver terms, cross-zone reason | SCHS-29, SCHS-44, SCHS-45 |
| P7 | Daily view, weekly summary, exception report, run summary, Reports tab, export | SCHS-26, SCHS-39, SCHS-27, SCHS-40, SCHS-41, SCHS-48 |
| P8 | Live-site data script, browser tests, requirement and wiki edits, tooling | SCHS-50, SCHS-53, SCHS-54, SCHS-55, SCHS-56, SCHS-57 |

Kill switch (unchanged): the site setting `scheduler.rules_version`, default 1; every story's new behaviour runs only at 2. The Wave 0 seams (SCHS-01 to SCHS-08) are behaviour-neutral.

---

## 3. Dependency graph and PR order

See `scheduler-build-stories.md`: section 3 (waves, conflict matrices and merge order) and section 4 (dependency graph, critical path, table of stories). Pull requests merge one at a time; building is parallel.

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

Each story owns its test files under `services/api/tests/scheduling/rules_v2/` (one file per story, `test_schs_NN_<name>.py`), so two stories never edit the same test file. Each test name starts with the row ID (`test_schr_hard_08_...`) so a search finds it. The chain is SCHR row, story, test file.

| Group | Rows | Owner rows | Stories |
|---|---|---|---|
| SCHR-PAR | 16 | 11 | SCHS-02, SCHS-10, SCHS-12, SCHS-13, SCHS-15, SCHS-17, SCHS-19, SCHS-23, SCHS-24, SCHS-33 |
| SCHR-CFG | 10 | 8 | SCHS-02, SCHS-06, SCHS-18, SCHS-52 |
| SCHR-HIER | 8 | 5 | SCHS-22, SCHS-32, SCHS-33 |
| SCHR-HARD | 13 | 11 | SCHS-10, SCHS-12, SCHS-14, SCHS-15, SCHS-17, SCHS-19, SCHS-21, SCHS-37 |
| SCHR-EXT | 12 | 10 | SCHS-10, SCHS-14, SCHS-17, SCHS-21, SCHS-32, SCHS-34, SCHS-36, SCHS-42, SCHS-44 |
| SCHR-INT | 26 | 21 | SCHS-10, SCHS-17, SCHS-24, SCHS-30, SCHS-32, SCHS-36, SCHS-37, SCHS-39, SCHS-46 |
| SCHR-CUT | 8 | 6 | SCHS-18, SCHS-19, SCHS-22 |
| SCHR-WKE | 6 | 5 | SCHS-20, SCHS-27, SCHS-32, SCHS-46 |
| SCHR-ZONE | 11 | 7 | SCHS-29, SCHS-44, SCHS-45 |
| SCHR-BRK | 10 | 6 | SCHS-23, SCHS-28, SCHS-34, SCHS-35, SCHS-43 |
| SCHR-OUT | 7 | 3 | SCHS-21, SCHS-26, SCHS-27, SCHS-39, SCHS-40, SCHS-41, SCHS-48 |
| SCHR-DEF | 6 | 5 | SCHS-30, SCHS-31, SCHS-47 |

Existing files that also carry assertions: `test_solver.py`, `test_site_off_days.py`, `test_multi_slot_hours.py`, `test_scheduling_api.py`, `test_automatic_planning.py`, `test_partial_outcomes.py`, `test_queue.py`, `test_rules.py`. Derived rows are covered by the tests of their story (one test each where the behaviour is checkable).

### 5.3 Traceability for every row whose status contains Owner (98 rows)

Chain: SCHR row, story, test file, planned test. Test names are planned; the full name is fixed when the test is written. The story status column is updated by the coordinator (Draft, In Dev, PR, Merged).

| Row | Status | Story | Test file | Planned test | Story status |
|---|---|---|---|---|---|
| SCHR-PAR-02 | Owner | SCHS-12 | `services/api/tests/scheduling/rules_v2/test_schs_12_weekly_off.py` | `test_schr_par_02_working_days_are_monday_tuesday_thursday` | Draft |
| SCHR-PAR-03 | Owner | SCHS-13 | `services/api/tests/scheduling/rules_v2/test_schs_13_default_slots.py` | `test_schr_par_03_the_weekly_off_weekday_is_a` | Draft |
| SCHR-PAR-04 | Owner | SCHS-15 | `services/api/tests/scheduling/rules_v2/test_schs_15_first_job.py` | `test_schr_par_04_cleaners_report_at_05_00_and` | Draft |
| SCHR-PAR-06 | Owner | SCHS-10 | `services/api/tests/scheduling/rules_v2/test_schs_10_durations.py` | `test_schr_par_06_the_job_duration_is_30_minutes` | Draft |
| SCHR-PAR-08 | Owner | SCHS-17 | `services/api/tests/scheduling/rules_v2/test_schs_17_interior_earliest.py` | `test_schr_par_08_the_earliest_start_of_an_interior` | Draft |
| SCHR-PAR-09 | Owner | SCHS-23 | `services/api/tests/scheduling/rules_v2/test_schs_23_break_rules.py` | `test_schr_par_09_the_break_for_all_crew_is` | Draft |
| SCHR-PAR-11 | Owner | SCHS-19 | `services/api/tests/scheduling/rules_v2/test_schs_19_weekday_cutoff.py` | `test_schr_par_11_the_customer_cutoff_has_two_settings` | Draft |
| SCHR-PAR-12 | Owner | SCHS-24 | `services/api/tests/scheduling/rules_v2/test_schs_24_ledger_service.py` | `test_schr_par_12_the_interior_entitlement_is_one_interior` | Draft |
| SCHR-PAR-13 | Owner | SCHS-24 | `services/api/tests/scheduling/rules_v2/test_schs_24_ledger_service.py` | `test_schr_par_13_a_service_week_runs_monday_to` | Draft |
| SCHR-PAR-15 | Owner | SCHS-33 | `services/api/tests/scheduling/rules_v2/test_schs_33_objective_order.py` | `test_schr_par_15_the_order_and_weights_of_the` | Draft |
| SCHR-PAR-16 | Owner | SCHS-12 | `services/api/tests/scheduling/rules_v2/test_schs_12_weekly_off.py` | `test_schr_par_16_the_weekly_off_applies_to_exterior` | Draft |
| SCHR-CFG-01 | Owner | SCHS-52 | `services/api/tests/scheduling/rules_v2/test_schs_52_config_guard.py` | `test_schr_cfg_01_no_rule_configuration_or_value_is` | Draft |
| SCHR-CFG-02 | Owner | SCHS-18 | `services/api/tests/scheduling/rules_v2/test_schs_18_site_settings_api.py` | `test_schr_cfg_02_every_value_is_editable_by_the` | Draft |
| SCHR-CFG-03 | Owner | SCHS-02 | `services/api/tests/scheduling/rules_v2/test_schs_02_site_settings.py` | `test_schr_cfg_03_defaults_are_seeded_by_migration_or` | Draft |
| SCHR-CFG-04 | Owner and Derived | SCHS-02 | `services/api/tests/scheduling/rules_v2/test_schs_02_site_settings.py` | `test_schr_cfg_04_the_solver_and_the_planner_read` | Draft |
| SCHR-CFG-05 | Owner and Derived | SCHS-02 | `services/api/tests/scheduling/rules_v2/test_schs_02_site_settings.py` | `test_schr_cfg_05_every_value_is_validated_on_save` | Draft |
| SCHR-CFG-06 | Owner | SCHS-02 | `services/api/tests/scheduling/rules_v2/test_schs_02_site_settings.py` | `test_schr_cfg_06_every_change_is_recorded_in_the` | Draft |
| SCHR-CFG-07 | Owner | SCHS-06 | `services/api/tests/scheduling/rules_v2/test_schs_06_run_context.py` | `test_schr_cfg_07_a_change_applies_from_the_next` | Draft |
| SCHR-CFG-09 | Owner and Derived | SCHS-52 | `services/api/tests/scheduling/rules_v2/test_schs_52_config_guard.py` | `test_schr_cfg_09_the_existing_constants_listed_in_hardcoded` | Draft |
| SCHR-HIER-02 | Owner | SCHS-32 | `services/api/tests/scheduling/rules_v2/test_schs_32_two_pass.py` | `test_schr_hier_02_hard_constraints_are_never_broken_by` | Draft |
| SCHR-HIER-04 | Owner | SCHS-33 | `services/api/tests/scheduling/rules_v2/test_schs_33_objective_order.py` | `test_schr_hier_04_the_priority_order_in_the_sheet` | Draft |
| SCHR-HIER-05 | Owner and Derived | SCHS-33 | `services/api/tests/scheduling/rules_v2/test_schs_33_objective_order.py` | `test_schr_hier_05_where_the_sheet_s_list_puts` | Draft |
| SCHR-HIER-07 | Owner | SCHS-32 | `services/api/tests/scheduling/rules_v2/test_schs_32_two_pass.py` | `test_schr_hier_07_pass_a_and_pass_b_are` | Draft |
| SCHR-HIER-08 | Owner | SCHS-22 | `services/api/tests/scheduling/rules_v2/test_schs_22_hand_placement.py` | `test_schr_hier_08_jobs_placed_by_hand_and_jobs` | Draft |
| SCHR-HARD-01 | Owner | SCHS-14 | `services/api/tests/scheduling/rules_v2/test_schs_14_pin_existing.py` | `test_schr_hard_01_before_assigning_the_scheduler_checks_each` | Draft |
| SCHR-HARD-02 | Owner | SCHS-14 | `services/api/tests/scheduling/rules_v2/test_schs_14_pin_existing.py` | `test_schr_hard_02_a_cleaner_s_own_shift_end` | Draft |
| SCHR-HARD-03 | Owner | SCHS-14 | `services/api/tests/scheduling/rules_v2/test_schs_14_pin_existing.py` | `test_schr_hard_03_a_cleaner_is_never_given_two` | Draft |
| SCHR-HARD-04 | Owner | SCHS-15 | `services/api/tests/scheduling/rules_v2/test_schs_15_first_job.py` | `test_schr_hard_04_no_job_starts_before_the_cleaner` | Draft |
| SCHR-HARD-05 | Owner | SCHS-17 | `services/api/tests/scheduling/rules_v2/test_schs_17_interior_earliest.py` | `test_schr_hard_05_no_interior_starts_before_the_interior` | Draft |
| SCHR-HARD-06 | Owner | SCHS-10 | `services/api/tests/scheduling/rules_v2/test_schs_10_durations.py` | `test_schr_hard_06_every_exterior_and_every_interior_takes` | Draft |
| SCHR-HARD-07 | Owner | SCHS-12 | `services/api/tests/scheduling/rules_v2/test_schs_12_weekly_off.py` | `test_schr_hard_07_no_exterior_or_interior_is_planned` | Draft |
| SCHR-HARD-08 | Owner | SCHS-19 | `services/api/tests/scheduling/rules_v2/test_schs_19_weekday_cutoff.py` | `test_schr_hard_08_on_a_strict_day_monday_tuesday` | Draft |
| SCHR-HARD-09 | Owner | SCHS-21 | `services/api/tests/scheduling/rules_v2/test_schs_21_reasons.py` | `test_schr_hard_09_every_active_car_needs_one_exterior` | Draft |
| SCHR-HARD-10 | Owner | SCHS-37 | `services/api/tests/scheduling/rules_v2/test_schs_37_interior_limits.py` | `test_schr_hard_10_at_most_one_interior_is_planned` | Draft |
| SCHR-HARD-11 | Owner | SCHS-37 | `services/api/tests/scheduling/rules_v2/test_schs_37_interior_limits.py` | `test_schr_hard_11_at_most_one_interior_is_planned` | Draft |
| SCHR-EXT-01 | Owner | SCHS-21 | `services/api/tests/scheduling/rules_v2/test_schs_21_reasons.py` | `test_schr_ext_01_every_active_car_has_one_exterior` | Draft |
| SCHR-EXT-02 | Owner | SCHS-10 | `services/api/tests/scheduling/rules_v2/test_schs_10_durations.py` | `test_schr_ext_02_each_exterior_takes_a_fixed_30` | Draft |
| SCHR-EXT-03 | Owner | SCHS-32 | `services/api/tests/scheduling/rules_v2/test_schs_32_two_pass.py` | `test_schr_ext_03_all_exterior_jobs_of_the_day` | Draft |
| SCHR-EXT-04 | Owner | SCHS-21 | `services/api/tests/scheduling/rules_v2/test_schs_21_reasons.py` | `test_schr_ext_04_exterior_has_the_highest_service_priority` | Draft |
| SCHR-EXT-05 | Owner and Derived | SCHS-42 | `services/api/tests/scheduling/rules_v2/test_schs_42_early_capacity.py` | `test_schr_ext_05_among_plans_that_cover_the_same` | Draft |
| SCHR-EXT-06 | Owner | SCHS-42 | `services/api/tests/scheduling/rules_v2/test_schs_42_early_capacity.py` | `test_schr_ext_06_early_free_capacity_is_never_made` | Draft |
| SCHR-EXT-07 | Owner | SCHS-42 | `services/api/tests/scheduling/rules_v2/test_schs_42_early_capacity.py` | `test_schr_ext_07_a_free_slot_is_never_kept` | Draft |
| SCHR-EXT-08 | Owner | SCHS-17 | `services/api/tests/scheduling/rules_v2/test_schs_17_interior_earliest.py` | `test_schr_ext_08_the_time_between_the_first_job` | Draft |
| SCHR-EXT-10 | Owner | SCHS-44 | `services/api/tests/scheduling/rules_v2/test_schs_44_zones_solver.py` | `test_schr_ext_10_the_exterior_pass_minimises_zone_changes` | Draft |
| SCHR-EXT-11 | Owner and Derived | SCHS-36 | `services/api/tests/scheduling/rules_v2/test_schs_36_ledger_demand.py` | `test_schr_ext_11_a_subscription_with_a_weekly_or` | Draft |
| SCHR-INT-01 | Owner and Derived | SCHS-36 | `services/api/tests/scheduling/rules_v2/test_schs_36_ledger_demand.py` | `test_schr_int_01_an_interior_is_planned_for_a` | Draft |
| SCHR-INT-02 | Owner | SCHS-10 | `services/api/tests/scheduling/rules_v2/test_schs_10_durations.py` | `test_schr_int_02_each_interior_takes_exactly_30_minutes` | Draft |
| SCHR-INT-03 | Owner | SCHS-17 | `services/api/tests/scheduling/rules_v2/test_schs_17_interior_earliest.py` | `test_schr_int_03_no_interior_starts_before_07_00` | Draft |
| SCHR-INT-04 | Owner | SCHS-10 | `services/api/tests/scheduling/rules_v2/test_schs_10_durations.py` | `test_schr_int_04_a_visit_that_has_both_an` | Draft |
| SCHR-INT-05 | Owner and Derived | SCHS-36 | `services/api/tests/scheduling/rules_v2/test_schs_36_ledger_demand.py` | `test_schr_int_05_the_customer_s_interior_care_day` | Draft |
| SCHR-INT-06 | Owner | SCHS-24 | `services/api/tests/scheduling/rules_v2/test_schs_24_ledger_service.py` | `test_schr_int_06_the_default_entitlement_is_one_interior` | Draft |
| SCHR-INT-07 | Owner | SCHS-32 | `services/api/tests/scheduling/rules_v2/test_schs_32_two_pass.py` | `test_schr_int_07_pass_b_starts_only_after_all` | Draft |
| SCHR-INT-08 | Owner | SCHS-32 | `services/api/tests/scheduling/rules_v2/test_schs_32_two_pass.py` | `test_schr_int_08_exterior_first_is_a_planning_sequence` | Draft |
| SCHR-INT-09 | Owner | SCHS-32 | `services/api/tests/scheduling/rules_v2/test_schs_32_two_pass.py` | `test_schr_int_09_pass_b_respects_weekday_cutoffs_kept` | Draft |
| SCHR-INT-10 | Owner | SCHS-46 | `services/api/tests/scheduling/rules_v2/test_schs_46_fifo.py` | `test_schr_int_10_the_scheduler_places_as_many_weekday` | Draft |
| SCHR-INT-11 | Owner | SCHS-24 | `services/api/tests/scheduling/rules_v2/test_schs_24_ledger_service.py` | `test_schr_int_11_every_interior_carries_an_explicit_service` | Draft |
| SCHR-INT-12 | Owner and Derived | SCHS-46 | `services/api/tests/scheduling/rules_v2/test_schs_46_fifo.py` | `test_schr_int_12_pass_b_orders_eligible_entitlements_by` | Draft |
| SCHR-INT-13 | Owner | SCHS-46 | `services/api/tests/scheduling/rules_v2/test_schs_46_fifo.py` | `test_schr_int_13_if_the_interior_of_week_1` | Draft |
| SCHR-INT-14 | Owner | SCHS-30 | `services/api/tests/scheduling/rules_v2/test_schs_30_ledger_outcomes.py` | `test_schr_int_14_when_the_overdue_interior_is_done` | Draft |
| SCHR-INT-15 | Owner | SCHS-30 | `services/api/tests/scheduling/rules_v2/test_schs_30_ledger_outcomes.py` | `test_schr_int_15_week_2_s_entitlement_is_never` | Draft |
| SCHR-INT-16 | Owner | SCHS-30 | `services/api/tests/scheduling/rules_v2/test_schs_30_ledger_outcomes.py` | `test_schr_int_16_an_overdue_interior_keeps_its_original` | Draft |
| SCHR-INT-17 | Owner | SCHS-39 | `services/api/tests/scheduling/rules_v2/test_schs_39_weekly_summary.py` | `test_schr_int_17_reports_show_for_each_interior_the` | Draft |
| SCHR-INT-18 | Owner | SCHS-37 | `services/api/tests/scheduling/rules_v2/test_schs_37_interior_limits.py` | `test_schr_int_18_more_than_one_physical_interior_may` | Draft |
| SCHR-INT-20 | Owner and Derived | SCHS-24 | `services/api/tests/scheduling/rules_v2/test_schs_24_ledger_service.py` | `test_schr_int_20_every_service_week_that_a_subscription` | Draft |
| SCHR-INT-21 | Owner | SCHS-24 | `services/api/tests/scheduling/rules_v2/test_schs_24_ledger_service.py` | `test_schr_int_21_an_operational_miss_car_keys_capacity` | Draft |
| SCHR-INT-25 | Owner | SCHS-24 | `services/api/tests/scheduling/rules_v2/test_schs_24_ledger_service.py` | `test_schr_int_25_the_entitlement_model_replaces_the_custom` | Draft |
| SCHR-CUT-01 | Owner | SCHS-19 | `services/api/tests/scheduling/rules_v2/test_schs_19_weekday_cutoff.py` | `test_schr_cut_01_on_monday_tuesday_thursday_and_friday` | Draft |
| SCHR-CUT-02 | Owner | SCHS-19 | `services/api/tests/scheduling/rules_v2/test_schs_19_weekday_cutoff.py` | `test_schr_cut_02_a_job_is_never_scheduled_to` | Draft |
| SCHR-CUT-03 | Owner | SCHS-19 | `services/api/tests/scheduling/rules_v2/test_schs_19_weekday_cutoff.py` | `test_schr_cut_03_if_an_interior_cannot_fit_before` | Draft |
| SCHR-CUT-04 | Owner | SCHS-19 | `services/api/tests/scheduling/rules_v2/test_schs_19_weekday_cutoff.py` | `test_schr_cut_04_if_an_exterior_cannot_fit_before` | Draft |
| SCHR-CUT-05 | Owner | SCHS-22 | `services/api/tests/scheduling/rules_v2/test_schs_22_hand_placement.py` | `test_schr_cut_05_an_admin_who_places_a_job` | Draft |
| SCHR-CUT-06 | Owner | SCHS-18 | `services/api/tests/scheduling/rules_v2/test_schs_18_site_settings_api.py` | `test_schr_cut_06_the_three_cutoffs_are_named_in` | Draft |
| SCHR-WKE-01 | Owner | SCHS-20 | `services/api/tests/scheduling/rules_v2/test_schs_20_weekend_soft.py` | `test_schr_wke_01_on_saturday_and_sunday_the_service` | Draft |
| SCHR-WKE-02 | Owner | SCHS-32 | `services/api/tests/scheduling/rules_v2/test_schs_32_two_pass.py` | `test_schr_wke_02_the_scheduler_finishes_all_weekend_exteriors` | Draft |
| SCHR-WKE-03 | Owner | SCHS-20 | `services/api/tests/scheduling/rules_v2/test_schs_20_weekend_soft.py` | `test_schr_wke_03_a_weekend_exterior_or_interior_may` | Draft |
| SCHR-WKE-05 | Owner | SCHS-46 | `services/api/tests/scheduling/rules_v2/test_schs_46_fifo.py` | `test_schr_wke_05_eligible_outstanding_interiors_are_allocated_on` | Draft |
| SCHR-WKE-06 | Owner | SCHS-27 | `services/api/tests/scheduling/rules_v2/test_schs_27_exception_report.py` | `test_schr_wke_06_weekend_lateness_against_a_cutoff_is` | Draft |
| SCHR-ZONE-01 | Owner | SCHS-29 | `services/api/tests/scheduling/rules_v2/test_schs_29_home_zone.py` | `test_schr_zone_01_each_society_has_several_zones_and` | Draft |
| SCHR-ZONE-02 | Owner | SCHS-44 | `services/api/tests/scheduling/rules_v2/test_schs_44_zones_solver.py` | `test_schr_zone_02_the_scheduler_minimises_the_number_of` | Draft |
| SCHR-ZONE-03 | Owner | SCHS-44 | `services/api/tests/scheduling/rules_v2/test_schs_44_zones_solver.py` | `test_schr_zone_03_after_the_home_zone_jobs_are` | Draft |
| SCHR-ZONE-04 | Owner and Derived | SCHS-44 | `services/api/tests/scheduling/rules_v2/test_schs_44_zones_solver.py` | `test_schr_zone_04_before_a_cross_zone_assignment_the` | Draft |
| SCHR-ZONE-05 | Owner | SCHS-44 | `services/api/tests/scheduling/rules_v2/test_schs_44_zones_solver.py` | `test_schr_zone_05_movement_across_zones_is_part_of` | Draft |
| SCHR-ZONE-06 | Owner and Derived | SCHS-45 | `services/api/tests/scheduling/rules_v2/test_schs_45_cross_zone_reason.py` | `test_schr_zone_06_the_reason_for_each_cross_zone` | Draft |
| SCHR-ZONE-07 | Owner and Derived | SCHS-29 | `services/api/tests/scheduling/rules_v2/test_schs_29_home_zone.py` | `test_schr_zone_07_the_admin_sets_one_home_zone` | Draft |
| SCHR-BRK-01 | Owner | SCHS-43 | `services/api/tests/scheduling/rules_v2/test_schs_43_break_solver.py` | `test_schr_brk_01_the_scheduler_tries_to_give_each` | Draft |
| SCHR-BRK-02 | Owner | SCHS-43 | `services/api/tests/scheduling/rules_v2/test_schs_43_break_solver.py` | `test_schr_brk_02_if_the_break_conflicts_with_an` | Draft |
| SCHR-BRK-03 | Owner | SCHS-43 | `services/api/tests/scheduling/rules_v2/test_schs_43_break_solver.py` | `test_schr_brk_03_mandatory_exterior_coverage_and_hard_weekday` | Draft |
| SCHR-BRK-04 | Owner | SCHS-43 | `services/api/tests/scheduling/rules_v2/test_schs_43_break_solver.py` | `test_schr_brk_04_every_missed_break_is_flagged_in` | Draft |
| SCHR-BRK-05 | Owner | SCHS-28 | `apps/web/src/pages/breaks/BreakDialog.test.tsx` | `test_schr_brk_05_the_admin_can_change_the_break` | Draft |
| SCHR-BRK-06 | Owner | SCHS-23 | `services/api/tests/scheduling/rules_v2/test_schs_23_break_rules.py` | `test_schr_brk_06_the_site_has_the_default_break` | Draft |
| SCHR-OUT-01 | Owner | SCHS-26 | `services/api/tests/scheduling/rules_v2/test_schs_26_daily_view.py` | `test_schr_out_01_the_daily_cleaner_wise_view_shows` | Draft |
| SCHR-OUT-02 | Owner | SCHS-39 | `services/api/tests/scheduling/rules_v2/test_schs_39_weekly_summary.py` | `test_schr_out_02_the_weekly_summary_shows_completed_against` | Draft |
| SCHR-OUT-03 | Owner | SCHS-27 | `services/api/tests/scheduling/rules_v2/test_schs_27_exception_report.py` | `test_schr_out_03_the_exception_report_shows_unassigned_mandatory` | Draft |
| SCHR-DEF-01 | Owner | SCHS-31 | `services/api/tests/scheduling/rules_v2/test_schs_31_deferred_state.py` | `test_schr_def_01_at_execution_if_the_car_or` | Draft |
| SCHR-DEF-02 | Owner | SCHS-47 | `services/api/tests/scheduling/rules_v2/test_schs_47_deferral_replan.py` | `test_schr_def_02_a_deferred_service_is_tried_again` | Draft |
| SCHR-DEF-04 | Owner | SCHS-31 | `services/api/tests/scheduling/rules_v2/test_schs_31_deferred_state.py` | `test_schr_def_04_the_deferral_reasons_come_from_configuration` | Draft |
| SCHR-DEF-05 | Owner | SCHS-31 | `services/api/tests/scheduling/rules_v2/test_schs_31_deferred_state.py` | `test_schr_def_05_both_by_case_when_the_key` | Draft |
| SCHR-DEF-06 | Owner | SCHS-30 | `services/api/tests/scheduling/rules_v2/test_schs_30_ledger_outcomes.py` | `test_schr_def_06_a_pending_interior_does_not_expire` | Draft |

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
| S34 | Saturday, Creta, cutoff 08:30, Exterior 30, Interior 30: Exterior 08:00-08:30 then Interior 08:30-09:00 | Both placed; the Interior is flagged late; no job unassigned | SCHR-WKE-01, WKE-03, WKE-05, HIER-05 | P2 (SCHS-20) |
| S35 | Saturday, all cleaners busy, earliest slot for the Creta is 09:00 | Exterior 09:00-09:30 placed. Interior 09:30-10:00 only if the 09:30-10:00 break is not due; if due, the Interior is in a later slot | SCHR-WKE-01 to 03, BRK-02, HIER-05, HIER-07 | P2 (SCHS-20); Interior part P4 (SCHS-43) |
| S36 | Thursday, same Creta, cutoff 08:30 | Exterior by 08:30; the Interior is not planned at 08:30-09:00; it is unassigned or deferred with the reason Customer cutoff and reported | SCHR-CUT-01 to 03, HARD-08 | P2 (SCHS-19) |

### 5.5 Property tests

Story SCHS-58, file `services/api/tests/scheduling/rules_v2/test_schs_58_properties.py`.

Plain pytest with seeded random generators (no new dependency; gate OG10 if `hypothesis` is wanted). Generate 200 random days (cleaners, windows, cars, cutoffs, entitlements) per run and check: no two jobs overlap for a cleaner or a car; every job inside a cleaner window; nothing before first-job time; no Interior before the Interior-earliest time; no job on the weekly-off day; on strict days no job ends after its cutoff; at most one Interior per car per service week and per day; Exterior count never decreases when capacity is added; same input gives the same output. Story SCHS-58; file `services/api/tests/scheduling/rules_v2/test_schs_58_properties.py`.

### 5.6 Configuration guard tests (SCHR-CFG-09)

Story SCHS-52, `services/api/tests/scheduling/rules_v2/test_schs_52_config_guard.py`:
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

Sizes, waves, dependencies, the critical path and the merge order are in `scheduler-build-stories.md` section 4: 58 stories in 5 waves; critical path SCHS-01, 02, 06, 32, 44, 45. The owner decides the order and when each wave starts (OG1).

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
