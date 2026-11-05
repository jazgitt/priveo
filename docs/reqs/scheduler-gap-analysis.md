# Scheduler gap analysis: Scheduling Rules v1.2 against the code

**Status:** Draft v0.3, 05-Nov-26 (owner decisions and the no-hardcoding instruction applied). Companion to `scheduler-requirements.md` (the SCHR- requirements). Checked against `main` at migration head 0050 (commit 3ef295c). Nothing in the code or in the existing requirement rows has been changed. The owner answered the 16 questions on 05-Nov-26 (requirements file, section 13); data updates on live sites still need the owner's go-ahead.

**Reading the evidence.** Paths are under `services/api/app/` unless they start with `apps/`. `file:line` was checked in this work tree. "S, M, L" are rough sizes: S under a day, M a few days, L a week or more, for one engineer including tests.

## 1. What the scheduler does today

- One CP-SAT solve for one site and one day, with all three services together (`scheduling/service.py:720` calls `solve_day`, `scheduling/solver.py`). Start times fall on a 5-minute grid (`solver.py:14`).
- The objective maximises minutes placed (`_PLACED`, `solver.py:16`), then penalises a late job (`_LATE`, line 17), then prefers earlier starts (`_EARLY`, line 18; objective lines 123 to 129).
- A cutoff is soft: a job that cannot meet it is still placed and flagged `late` (`solver.py:126-129`, `service.py:891`).
- A vehicle is never worked on by two cleaners at the same time (`solver.py:119-121`, `133-134`). Two jobs of one car can go to different cleaners.
- Demand: Exterior every day; Interior on the subscription's interior care weekday, or from a Weekly or Cycle pattern (`service.py:123-170`, `customers/schedule_pattern.py:64-76`). A weekday with no working slot for a service gives no demand (`service.py:235-247`).
- No zones, no break, no reporting time, no service week, no first-in-first-out, no second pass.

## 2. Rule by rule

### 2.1 Parameters (sheet table)

| # | Sheet item | Current behaviour and evidence | Gap | Required change | Size |
|---|---|---|---|---|---|
| G01 | Working days, weekly off Wednesday ("Yes - site working slots") | Per-site working slots hold the open weekdays (`directory/models.py:97-110`). A weekday with no slot gives no demand (`service.py:235-247`, ADM-CAP-08, test `tests/scheduling/test_site_off_days.py`). Default slots open all 7 days (`directory/seed.py:25-30`, `days=list(range(7))`; `directory/defaults.py:14-19`). Wednesday is not special anywhere (`grep` of the API finds no weekday-2 rule). Capacity counts crew windows on every day, even a site-off day (`service.py:409`). Crew working hours are per cleaner and separate from site slots (`scheduling/rules.py:73-95`, `scheduling/service.py:296-322`). | The mechanism exists. The default and the existing data say "open every day". A cleaner whose own hours include Wednesday still shows capacity. Docs say there is no rest day. | Data: change the seed default and, with approval, update existing sites' slots. API: `availability()` returns no window on a day the site is off for both cleaning services; capacity follows. Portal: Slots tab shows the weekly off clearly. Docs: see section 5. Tests: update `test_site_off_days`, `test_multi_slot_hours`. | M |
| G02 | Reporting 05:00, first job 05:30 ("No - add to settings at site level, default for each crew, editable per crew") | No field. A cleaner's window start is the earliest a job can start (`solver.py:111`). Model default for a cleaner is 06:00 to 11:00 (`scheduling/models.py:45-46`); new crew take 05:00 to 11:00 from the site slots (`crew/service.py:286-322`). | Missing: reporting time, first-job time, site default, per-cleaner override. | Migration: site settings store (G27) and nullable `scheduling_crew.reporting_minute`, `first_job_minute`. `availability()` applies the first-job floor to the first window of the day. Crew detail shows site default and an override field; HoursEditor (`apps/web/src/pages/crew/HoursEditor.tsx`) gets two inputs. | M |
| G03 | Job duration 30 / 30 / 60 ("Yes") | Durations 20, 20 and 120 (`directory/defaults.py:9`, copy in `scheduling/models.py:24`, read by `directory/lookup.py:105-110`). Admin can edit them (`apps/web/src/pages/reference/ServicesTab.tsx:14-30`). A job copies its duration when it is created (`service.py:644`); a re-run refreshes only the cutoff of an existing job (`service.py:652-653`), so existing jobs keep 20 minutes. Extra add-ons default to 20 (`directory/defaults.py:92`, `102`). | Defaults are 20. Existing Draft and Scheduled jobs would stay at 20. The Demand fallback constant duplicates the default. Capacity text says 20 (ADM-CAP-01). | Change the defaults to 30 and 30 (and the two extra add-ons, with approval). Update live rows by an admin edit or a data migration. A re-run refreshes `duration_minutes` of jobs that are Scheduled and not frozen. Remove the duplicate constant. | S to M |
| G04 | Combined 60 minutes, jobs consecutive or apart, possibly different cleaners | Two separate jobs, one per service; the solver allows different cleaners and prevents overlap on the same car (`solver.py:119-134`). | Works. Only labels (capacity, board) assume 20. | None for the solver. Check capacity and card text. | S |
| G05 | Interior earliest 07:00, every day ("No - build configuration") | None. A Cleaning-Internal job can use any cleaner window and any service slot (`service.py:575-580`, `701-717`; the solver already accepts per-job allowed windows, `solver.py:88-92`). The Cleaning-Internal working slot could be set to 07:00 by hand today (ADM-SVS-02). Hand moves check the service slots (`service.py:811-891`). | No dedicated setting; relying on the slot start is fragile and would also stop a later slot edit from breaking the rule. | New site setting `interior_earliest_minute`. `service_windows()` returns `max(slot start, setting)` for Cleaning-Internal. Hand moves use the same function. | S |
| G06 | Break 09:30 to 10:00, priority over Interior, date-range override with cues ("Yes partially") | Not a break. What exists: a cleaner can have extra working slots on a day, so a gap can be left by hand (`rules.py:73-95`, ADM-CRW-25); the Board draws "Not working" for gaps (`apps/web/src/pages/schedule/CardBoard.tsx:287`). Nothing is planned around a break, nothing is flagged. | No break setting, no date range, no solver rule, no missed-break flag. | New site setting for the default break, and a break-rule table with start date, end date, optional cleaner, times, on or off. Portal: break dialog with Today, Tomorrow, Date range. Solver: break as a soft block in Pass A and a hard block in Pass B (see G17). Capacity minus break. Output flag. | L |
| G07 | Customer cutoff, strict on weekdays ("No - do the implementation") | Soft: late jobs are placed and flagged (`solver.py:126-129`; `service.py:891`). Exceptions: after a freeze and for add-on bookings the allowed window is already cut at the cutoff (`service.py:701-707`). | Weekday cutoff must be a hard limit for both services; an Exterior or Interior that cannot fit must stay unassigned with a reason. | Solver: for jobs on a strict day add a hard end limit (the existing `windows` argument can carry it). Keep the soft penalty for weekend days. Unplaced reason "Weekday cutoff". Settings `weekday_cutoff_hard`, `weekend_cutoff_flexible`, `weekend_weekdays`. Hand moves: warn and flag in the exception report (owner, 05-Nov-26). Tests: `test_solver`, `test_scheduling_api`. | M |
| G08 | Weekend flexible after mandatory Exteriors | The existing soft penalty is flexible everywhere. No weekend rule. | Weekend Exteriors first, then Interiors; lateness minimised in order. | Follows from G07 and G17. | S |
| G09 | Interior entitlement, one per service week; carry forward; credit to original week ("No - add in rule hierarchy") | No service week anywhere (`Job` has no such column, `scheduling/models.py:117-151`). Interior is due only on the subscription's weekday or pattern day (`service.py:151`, `customers/schedule_pattern.py:64-76`). A missed Interior is not carried: ADM-SVS-01 and customer business rule 2 say it is lost; the admin may reschedule it for the next day only (ADM-CNC-10), through a follow-up job (`Job.source_job_id`, `scheduling/models.py:136-138`; `service.py:205-228`). | The whole entitlement model is missing: ledger, creation, week definition, carry, credit, waiver, reports. It contradicts "lost and not made up". | Migration: table `interior_entitlements` (subscription or vehicle, service week start, status, job, completed on, waived reason) and `jobs.service_week_start`. Service: `ensure_entitlements(site, days)`; demand for Interior comes from pending entitlements, not from the weekday. Settings `interior_entitlement_per_week`, `service_week_start`. Status changes follow the job outcome (Completed credits the ledger row; Could not complete returns it to Pending). Backfill: create the current week's entitlement for Active subscriptions with an interior plan; do not invent past debt (approval). | L |
| G10 | One Interior per service week and per car per day | Not enforced: nothing links an Interior to a week. | Hard rule. | Unique constraint on the ledger row and the job link; solver constraint of at most one Interior per car per day. | S after G09 |
| G11 | First in, first out by service week | No ordering except the 5-minute early term. | Missing. | Pass B orders entitlements by service week, then wait, then cutoff tightness; weights separated by a large factor so older weeks always win. | M after G09 |
| G12 | Customer-preferred Interior weekday not binding | The preferred day is the demand trigger (`service.py:151`); the customer app and the calendar show it (`changes/projection.py:18-29`; customer ONB-18, SUB-08). | Preferred day cannot stay a promise. The customer calendar would show Interior on a day the scheduler may not use. | Keep the field as a tie-break. Calendar projection shows the planned job once it exists, and "Interior this week" before that. Wording of ONB-18 and SUB-08 (approval). | M |

### 2.2 Rule groups 01 to 11

| # | Sheet rule | Current behaviour and evidence | Gap | Required change | Size |
|---|---|---|---|---|---|
| G13 | 01 Availability, shifts, no overlap, nothing before 05:30, Wednesday off | Availability, exceptions, shift end and cleaner no-overlap exist (`service.py:296-322`, `solver.py:111-112`, `132`). Roles: a Trainee adds no capacity (`rules.py:59`). Nothing before 05:30; Wednesday: see G01, G02. | First-job floor and the weekly off. | See G01, G02. | S |
| G14 | 02 Exterior mandatory daily; report shortfall | Exterior is due every day for an Active subscription (`service.py:142-170`). Unplaced jobs go to Unscheduled with a reason text (`service.py:730`, solver messages `solver.py:92`, `102`, `144`, `151`). Patterns can remove Exteriors (`schedule_pattern.py:64-76`). | No shortfall figure; no structured reason; patterns may break "every working day". | Reason codes, shortfall in minutes and cars in the run summary and report (G24). Patterns are kept and feed the preferred days only (owner, 05-Nov-26). | M |
| G15 | 03 Cutoff policy | See G07, G08. | | | |
| G16 | 04 Home zone, spill into other zones in spare capacity, reason recorded (owner, 05-Nov-26) | `Zone` (`directory/models.py:33-43`) and `Vehicle.zone_id` (`customers/models.py:71`) exist and are managed in Site Setup (ADM-REF-08, `apps/web/src/pages/reference/ZonesTab.tsx`). The scheduler reads zones only to show a label (`service.py:1072-1075`, `1243-1258`). No link from a cleaner to a zone. No zone term in the solver. No place to store a cross-zone reason. | Missing: home zone, fill-home-first preference, cross-zone spill, reason. | Migration: nullable `scheduling_crew.home_zone_id` (one home zone per crew member, set by the admin); `jobs.cross_zone_reason`. Solver: a penalty for a job outside the cleaner's home zone and for zone switches in a day, so the home zone is filled first and other zones take spare capacity; cross-zone work may not push a home-zone job past its cutoff. Portal: home-zone picker on Crew detail. The simpler model (one field, no pre-check of the owner) lowers the estimate from L to M. | M |
| G17 | 05 Interior eligibility; 07:00; 60-minute visit; defer with reason; one per service week | See G03, G04, G05, G09, G19. | | | |
| G18 | 06 Early free-slot strategy | `_EARLY` (`solver.py:18`, `124`) pushes every job as early as possible. That leaves free time at the end of the shift, which is what the sheet says it does not want. Nothing separates 05:30 to 07:00 from 07:00 on. | Opposite effect; no notion of usable free capacity. | In Pass A, replace the global "earlier start" term with a "usable free minutes" term (free cleaner minutes at or after 07:00 and before the latest weekday cutoff of a pending Interior), lower than coverage, zone and weekend lateness. Keep a small early-start term as a tie-break. Capacity page shows the free 05:30 to 07:00 band as available for onboarding. | M |
| G19 | 05 and 11 Deferral: car or keys not available, never mark done, retry in next feasible slot | The crew marks "Could not complete" with a reason (`scheduling/outcomes.py:50-55`; reasons in `directory/defaults.py:39-50`). The visit can be Partially Completed (ADM-CNC-09). Rescheduling is a decision of the admin or a Manager, next day only (ADM-CNC-10, ADM-CNC-06). No automatic retry. Job statuses have no Deferred value (`scheduling/models.py:25`). | No automatic reattempt and no "Deferred" word. A decision rule conflict with ADM-CNC-10. | Treat "Could not complete" on an Interior as a deferral: the ledger row returns to Pending (G09) and Pass B picks it up on the next planned day. Show Deferred in the portal and reports. Deferred is a new job state used when the key or the car is not available; partial completion keeps the ADM-CNC-10 next-day rule (owner, 05-Nov-26). | M |
| G20 | 07 Break | See G06. | | | |
| G21 | 08 Two passes | One solve with all jobs (`service.py:720`). | Pass A (Exteriors) then Pass B (Interiors) with Pass A fixed. | In `run_schedule`, per day: split `solver_jobs` by service; solve Exteriors; pass their placements as `fixed`; solve Interiors in the gaps. The solver already supports `fixed` jobs (`solver.py:58`, `78`). Objective becomes ordered (section 3 of the requirements): either sequential solves that freeze each objective's value, or weights separated by orders of magnitude. Keep `num_workers=1` and the seed for repeatable plans (`solver.py:138-140`). Days planned in date order so the ledger flows (G09). Re-run, freeze, late assignment and hand moves keep working with fixed jobs. | L |
| G22 | 09 Entitlement accounting | See G09, G10, G11. | | | |
| G23 | 10 Priority order | There is an ordering only between placed minutes, late and early. | The full ordering and its documentation. | Constants and a short test per level. | M |
| G24 | 11 Outputs | Board and filters (`service.py:1113`), Needs scheduling (`1188`), crew day (`1216`), capacity per day (`360`), skipped list (`1138`), run summary (placed, unscheduled, late: `service.py:748-755`). No weekly summary, no exception report, no break, no free-slot list, no cross-zone reason, no overdue days. | Three reports missing. | New read-only endpoints under `/v1/admin/scheduling`: daily cleaner view, weekly summary, exception report. Portal: a Reports tab on the Schedule page. Extend the run summary and the schedule history. | L |

### 2.3 Cross-cutting

| # | Item | Current behaviour and evidence | Gap | Required change | Size |
|---|---|---|---|---|---|
| G25 | Where site-level settings live | `system_settings` is global (`directory/models.py:139-148`, registry `directory/settings_registry.py:32-78`). Per-site data exists only for working slots, zones and the society row. | No per-site setting store. | New table `society_settings` (site, key, value) or typed columns on a new `site_scheduling` row; resolution order in section 1 of the requirements; audit through `DirectoryAudit` with `society_id` (`directory/models.py:172-187`). | M |
| G26 | Planning period against service week | Week start Sunday (`settings_registry.py:53`), used by `service.run` (`service.py:768-805`), automatic planning (`scheduling/automatic.py:20-26`) and the Schedule page default (`apps/web/src/pages/schedule/SchedulePage.tsx:152`). The 8 PM freeze is the day before the first day (`rules.py:14-20`). | Service week (Monday) is a different thing and can cross a Sunday-start period. | The planner computes the service week of each day separately. Automatic planning needs no change, but plans days in date order and creates ledger rows first. | S |
| G27 | Settings screens | Site Setup has Slots, Services, Zones, Societies tabs (`apps/web/src/pages/reference/`). Preferences hold the period (`apps/web/src/pages/settings/`). Crew detail has hours and exceptions (`apps/web/src/pages/crew/`). | No place for the new settings, the break dialog or the zone owners. | A "Scheduling rules" panel in Site Setup; owner and override fields on Crew detail; a break dialog; use `useAppMutation` and `useConfirm` as the portal rules require (CLAUDE.md). | M |
| G28 | Hand placement | `move_job` refuses outside hours, outside the service slot and overlap; it flags a late job (`service.py:811-891`). | Does not know the weekly off (through slots it does), the first-job time, the Interior-earliest time or the break. | Reuse the shared window function (G02, G05). Break: warn only. | S |
| G29 | Capacity page | Minutes of crew time against 20 or 120 per job (`service.py:360-437`, ADM-CAP-01). | Break, weekly off, 30-minute jobs, free 05:30 to 07:00 minutes. | Subtract the break and the off days; show the free early band. | M |
| G30 | API contract and apps | `packages/api-contract/openapi.json` exports the API. The Flutter app reads `lib/core/api/api.g.dart`. | New and changed fields. | Export the contract and run `dart run tool/gen_api.dart` after each API change (CLAUDE.md). The crew app day view (job card list) may show the break and the cross-zone note; not inspected in detail here. | S |
| G31 | Customer calendar and notices | The calendar projection uses the preferred weekday (`changes/projection.py:18-29`). | See G12. | See G12. | M |
| G32 | Audit and history | `scheduling_events` records runs (`scheduling/models.py:173-183`). | New settings and break changes need audit rows. | Use `DirectoryAudit` with a new entity name. | S |

## 3. New configuration settings required

All are described in the configuration table of `scheduler-requirements.md` (section 1). Summary:

| Key | Default | Scope | New or existing |
|---|---|---|---|
| Weekly off (working slot days) | Wednesday closed | Site | Existing, new default |
| `site.reporting_minute` | 300 (05:00) | Site, crew override | New |
| `site.first_job_minute` | 330 (05:30) | Site, crew override | New |
| `DirectoryService` duration, Exterior and Interior | 30, 30 | Global | Existing, new default |
| `site.interior_earliest_minute` | 420 (07:00) | Site | New |
| `site.break_enabled`, `site.break_start_minute`, `site.break_end_minute` | On, 570, 600 | Site, crew, date range | New (with an override table) |
| `site.weekday_cutoff_hard` | On | Site | New |
| `site.weekend_cutoff_flexible` | On | Site | New |
| `site.weekend_weekdays` | Saturday, Sunday | Site | New |
| `schedule.interior_entitlement_per_week` | 1 | Global | New |
| `schedule.service_week_start` | Monday | Global | New |
| Crew home zone (`scheduling_crew.home_zone_id`) | none | Crew | New field |
| `site.cross_zone_help_allowed` | On | Site | New |

New tables and columns (migration 0051 onward; confirm the number at build time, because other branches may take it): `society_settings`; `scheduling_crew.reporting_minute`, `scheduling_crew.first_job_minute`; `break_rules`; `interior_entitlements`; `jobs.service_week_start`, `jobs.cross_zone_reason`; `scheduling_crew.home_zone_id`.

## 3a. Hardcoded values to remove (SCHR-CFG-01, SCHR-CFG-09)

Owner instruction of 05-Nov-26: nothing is hardcoded. Each constant below moves into configuration, seeded by migration, read through `directory/lookup.py`.

| Where | Constant | Target setting and place |
|---|---|---|
| `scheduling/solver.py:14` | `STEP = 5` | `scheduler.grid_minutes`, Settings, Schedule tab. The web `SNAP = 5` (`apps/web/src/pages/schedule/Board.tsx:6`) reads the same value from the board response |
| `scheduling/solver.py:16-18` | `_PLACED`, `_LATE`, `_EARLY` weights | `scheduler.weight_*` and `scheduler.objective_order`, Site Setup, Scheduling rules (confirm on edit); new weights for zone, break, FIFO |
| `scheduling/solver.py:50` | `max_seconds = 10.0` | `scheduler.solve_seconds`, Settings, Schedule tab |
| `scheduling/solver.py:139-140` | `num_workers = 1`, `random_seed = 7` | `scheduler.workers`, `scheduler.seed`, same tab |
| `scheduling/solver.py:89` | window default `(0, 1440)` | Derived from the service's working slots; no default window |
| `scheduling/service.py:578` | fallback windows `(0, 1440)` for Deep Spa and `(300, 660)` for cleaning | Working slots seeded per site (Slots tab); no fallback, a missing slot is an error |
| `crew/service.py:303` | `spans = [(300, 660)]` for a site with no slots | Same: seeded slots only |
| `scheduling/models.py:45-46` | crew model defaults `360` and `660` | Taken from the site's working slots and `site.first_job_minute` when a crew record is made |
| `scheduling/models.py:24` | `DURATIONS` (also used by `Demand.duration`, `service.py:56`) | `directory_services.duration_minutes` through `lookup.durations`; remove the constant |
| `directory/defaults.py:9` | `DURATIONS` 20, 20, 120 | Seed in a migration or `seed.py` (30, 30, 120); not a code default |
| `directory/defaults.py:14-19` | `DEFAULT_SLOT_WINDOWS` | Seed only, with the weekly-off weekday left out |
| `directory/defaults.py:92`, `102` | extra add-on duration 20 | Seed value, admin editable |
| `scheduling/rules.py:12-15` | `UNFREEZE_CODE`, `FREEZE_HOUR`, `CUSTOMER_HOUR` | Already registry keys (`settings_registry.py:55-61`); delete the constants and read the keys |
| `scheduling/automatic.py:59`, `87` | retry after 30 minutes and 5 minutes | Registry keys on the Schedule tab |
| `directory/defaults.py:6`, `customers/models.py:9` | `WEEKDAYS` tuples | Calendar names only, no rule in them. One shared calendar constant; the weekly-off day, weekend days and service-week start come from settings (`site.weekend_weekdays`, `schedule.service_week_start`) |
| `scheduling/models.py:25-26`, `JOB_STATUSES`, `CREW_ROLES` | status and role names | Fixed vocabulary of the data model, not scheduling rules; the new Deferred state is added here |
| `directory/defaults.py:39-50` | could-not-complete reasons | Already a table (`cnc_reasons`); the constant is only the seed |
| `directory/settings_registry.py:53-65` | defaults inside the registry (week start 6, cutoff 09:00, step 30) | Keep the registry for type and range; seed the values by migration |

Admin sections: reuse the Settings page (Schedule tab lists every `schedule.*` key by itself, `SettingsPage.tsx:35`, `104-106`), the Slots, Services, Zones tabs and Crew detail. New: a Scheduling rules section in Site Setup (per-site values, objective order and weights), a break dialog (Site Setup and Crew detail), and a home-zone field on Crew detail.

## 4. Dependency order

1. Owner decisions: done on 05-Nov-26 (requirements file, section 13). Update the requirement files before building.
2. Site settings store (G25) before everything that is site-level.
3. Durations, weekly off, first-job floor, Interior-earliest (G01 to G05): no solver redesign.
4. Hard weekday cutoff (G07, G08): small solver change.
5. Two passes and ordered objectives (G21, G18, G23) before the break and early-capacity terms.
6. Break (G06) after the two passes.
7. Entitlement ledger (G09, G10) before FIFO (G11), before deferral (G19) and before the Interior reports.
8. Zones (G16) are independent of the ledger and can run in parallel with step 7 but touch the same solver, so run them serially.
9. Outputs (G24, G29) last, because they read everything.

## 5. Existing requirement IDs and documents that must change (not changed in this pull request)

These are listed, not edited.

**Admin file (`admin-functional-requirements.md`)**

| ID | Why it changes |
|---|---|
| ADM-SVS-05 | "Every day is open: there is no rest day" becomes Wednesday off. |
| ADM-SVS-09 | 20-minute durations become 30. |
| ADM-SVS-10 | Interior is due by entitlement, not "on the customer's interior care day". |
| ADM-SVS-01 | "That week's Cleaning-Internal is lost and not made up" conflicts with carry-forward. |
| ADM-SCH-04 | Inputs now include entitlements, zones, break, reporting time. |
| ADM-SCH-05 | "Greatest use of the crew's capacity" is replaced by the ordered objectives. |
| ADM-SCH-07 | "A visit should finish by the cutoff ... flagged" becomes hard on weekdays. |
| ADM-SCH-08 | Unscheduled reasons become structured. |
| ADM-SCH-09 | Week starts Sunday: say the service week starts Monday, separately. |
| ADM-SCH-33 | The 5-minute snap and the 20-minute card width; the Board needs the break block. Check against 30-minute jobs. |
| ADM-SCH-41 | Weekly and Cycle patterns against entitlement and the Exterior-every-working-day rule. |
| ADM-SCH-26, ADM-CNC-03, ADM-CNC-06, ADM-CNC-10 | Reschedule for the next day only against automatic deferral. |
| ADM-CAP-01, ADM-CAP-08 | 20-minute minutes, the break, the weekly off, the early band. |
| ADM-PRF-01 | Add the service week start beside the period. |
| ADM-SUB-10 | Custom interior day, parked: decide with the entitlement model. |
| ADM-CRW-04, ADM-CRW-25 | Reporting time, first-job time, per-cleaner overrides, zone ownership. |
| ADM-REF-08 | Zones gain owners. |
| ADM-SET-07 | Audit entries for the new settings. |
| Business rules 4, 5, 6 (section 10) | "No rest day", "about 20 minutes", the planning period. |
| Section 12 (needed by / covered by), section 13 (open questions, now answered), data entities (Service, Society, Crew) | New rows and entities. |

**Customer file (`customer-app-functional-requirements.md`)**

| ID | Why it changes |
|---|---|
| Customer business rule 1 | "No fixed rest day" becomes Wednesday off. |
| Customer business rule 2 | "That week's interior is lost and not made up" against carry-forward. |
| ONB-16 | Helper text about the cutoff: a weekday cutoff is now firm. Decide on a warning or limit. |
| ONB-18, SUB-08 | The interior care day becomes a preference. |
| PAY-02 | "Exterior cleaning 7 days a week" in the plan inclusions. |
| SKIP-, PAUSE- rows, CAL-08 | Effect on the entitlement of a skipped or paused week; the calendar view of Interior. |
| SCHED-01 | Terminology: the customer change deadline against the service cutoff. |

**Crew file (`crew-functional-requirements.md`)**

| ID | Why it changes |
|---|---|
| CRW-SCH-05 | "20 minutes for Cleaning-Internal" and "on the interior care day". |
| CRW-SCH-10 and the queue rows | Trainee follows the Member, zone ownership, break block in the day. |

**Other documents**

| Document | Why it changes |
|---|---|
| `docs/coverage/business-rules.md` (customer rules 1, 2 and 5; admin rules 4, 5 and 6) | Rows quote the old rules. |
| `docs/coverage/data-entities.md` | New entities. |
| `docs/feature-status.json` | New SCHR- IDs (done as drafts in this work); changed rows go back to Draft. |
| `wiki/Scheduling_and_capacity.md`, `wiki/Glossary.md`, `wiki/Site_setup.md`, `wiki/Workforce_management.md` | Durations, rest day, week start, new settings. Run `wiki/validate.py` after. |
| `README.md` | The prototype-differences table says "There is no rest day". |
| `docs/reqs/owner-decisions-2026-11-05.md` (or a new dated file) | Record the owner's answers of 05-Nov-26. |
| `docs/design/scheduler-board-redesign.md` | Break block, 30-minute card heights, snap. |
| `tools/priveo-reqs/hooks/register.ts` | The `REQS` list holds only three files. A fourth file is not checked for IDs and its rows are dropped from `feature-status.json` the next time `/fstatus` runs. Add the new file to `REQS` (a tool change, not done here). |

## 6. Recommended implementation sequence

| Phase | Content | Gaps | Size | Notes |
|---|---|---|---|---|
| 0 | Owner decisions; update the requirement files | all | S | Gate for all other phases. |
| 1 | Site settings store; durations 30/30 and refresh on re-run; weekly off default, availability and capacity; reporting and first-job time; Interior-earliest; portal panel; audit | G01 to G05, G13, G25, G27, G28, G32 | L | No solver redesign. Releasable alone. Prod data update needs approval. |
| 2 | Hard weekday cutoff, weekend flexible, structured unassigned reasons | G07, G08, G14 | M | Releasable alone. Shows the capacity problem early (section 7). |
| 3 | Two passes and ordered objectives; usable early capacity | G17, G18, G21, G23 | L | The core solver change. Needs the full solver test rewrite. |
| 4 | Break: settings, override table, dialog, solver, flag, capacity | G06, G29 | L | After phase 3. |
| 5 | Entitlement ledger, service week, FIFO, carry, deferral, calendar projection | G09 to G12, G19, G31 | L | Backfill with approval. Plans days in date order. |
| 6 | Zones: home zone, spill, reasons | G16 | M | Serial after phase 5. |
| 7 | Outputs: daily view, weekly summary, exception report, run summary | G24, G29 | L | Last. |
| 8 | Docs, wiki, coverage files, tool list | section 5 | M | Starts right after phase 0 for the requirement files; wiki after each release. |

Each phase follows the merge rule in CLAUDE.md: local checks first (including the PostgreSQL stage, because the API and the database change), draft pull request while iterating, then ready.

## 7. Risks

**Capacity with 30-minute jobs.** The figures use the default window 05:30 to 11:00, a 30-minute break and 30-minute jobs. They are derived arithmetic, not measured.

- One cleaner: 330 minutes, minus the break, is 300 minutes, so 10 jobs a day. The current plan puts 18 jobs of 20 minutes into 05:00 to 11:00.
- A car needs 6 Exteriors and 1 Interior a week, 7 jobs. One cleaner working 6 days serves about 8 to 9 cars. Today (7 Exteriors and 1 Interior at 20 minutes, 7 days) it is about 15 cars. That is a fall of roughly 45 percent. Existing sites will show over-capacity (ADM-CAP-04) the day the durations change.
- With the default cutoff of 09:00 (`settings_registry.py:62`), a cleaner has 05:30 to 09:00, 210 minutes, 7 jobs, before the cutoff. A cleaner with 7 cars fills the whole strict-day morning with Exteriors. No Interior fits before a 09:00 cutoff, so every Interior goes to Saturday or Sunday, and at most about 6 fit there for that cleaner. The rest is carried over and grows every week. The sheet's goal of "maximise weekday Interiors" is limited by customers' own cutoffs.
- Under the hard weekday cutoff, a car with a cutoff earlier than about 06:00 cannot be served on a strict day at all (first job 05:30 plus 30 minutes).

**Existing data.**

- Working slots of live sites open all 7 days; crew hours include Wednesday; customers with Wednesday as the interior care day; Weekly patterns that name Wednesday.
- Jobs already created keep 20 minutes (`service.py:652-653`). Frozen schedules that include Wednesday jobs: they need a decision (leave, or move).
- Customers have been told "7 days a week" and chose an interior care day. The backlog start: do not create debt for weeks that have passed.
- Payment plan text (`directory/defaults.py:59`) says "Exterior cleaning 7 days a week".
- Production releases need the owner's approval (CLAUDE.md, hosting).

**Tests and tooling.**

- Solver tests (`tests/scheduling/test_solver.py`), `test_site_off_days.py`, `test_multi_slot_hours.py`, `test_scheduling_api.py`, `test_automatic_planning.py`, add-on tests that assume 20 minutes (`tests/addons`), `tests/directory/test_directory.py`, `tests/customer_reads/test_calendar_projection.py`, and web tests for the Board (`apps/web/src/pages/schedule/Board.test.tsx`) and Services tab. Playwright browser tests that read board times.
- The solve time is limited to 10 seconds a day (`solver.py:138`); two passes double the calls. A weekly automatic run for many sites should be timed on the hosting limit before release.
- A fourth requirements file is outside the `/fstatus` tool (see section 5).

## 8. What could not be verified

- No code was run. Line numbers were read, not executed.
- The Flutter crew and customer screens were searched only for a break or rest-day feature (none found); their day views were not read in full.
- The Playwright and golden-image tests were not read in detail.
- The sheet's last owner note on reporting time is truncated in the document extraction ("... Allow edit / override at each c"). It is read as "each crew member". If it says something else, SCHR-PAR-04 and SCHR-PAR-05 need a check.
- Live databases were not checked: whether a site already has Wednesday closed, or whether durations have been edited, is not known from the code.
