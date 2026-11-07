# Priveo Car Concierge: Scheduler Requirements (Scheduling Rules v1.2)

**Status:** Draft v0.5 (Interior gap rule SCHR-INT-27 and the no-Interior case SCHR-INT-28 added, SCHR-INT-05 and SCHR-HIER-08 changed, 8 Nov 2026), v0.4 (worked examples for the weekend cutoff added to section 3, no row changed, 06-Nov-26), v0.3 (no-hardcoding rules SCHR-CFG added, 05-Nov-26), v0.2 (owner decisions of 05-Nov-26 applied), v0.1 (new file, 05-Nov-26). Written from the owner's "Priveo Scheduling Rules, Finalized v1.2" sheet of 05-Nov-26. Not yet approved by the owner. The existing requirement rows in the customer, admin and crew files are NOT changed by this file; the list of rows and documents that must change once the owner approves is in `scheduler-gap-analysis.md`.
**Scope:** The daily and weekly scheduler for car cleaning (Cleaning-External and Cleaning-Internal): the settings it reads, the rules it applies, the order in which rules win, the entitlement accounting for interior cleaning, and the reports it must give. Deep Spa is outside the sheet and keeps its current behaviour (ADM-ADD, ADM-SCH-30).
**Platforms:** The rules run in the API (`services/api/app/scheduling`). Settings and reports are shown in the React web portal. The crew app shows the resulting day (crew file).
**Language:** English only

## How this document was built

Sources:

- The owner's Scheduling Rules sheet, version 1.2, 05-Nov-26: the "Key operating parameters" table (with the owner's notes in the column "Currently implementation exists?") and rule groups 01 to 11, and the confirmed catch-up example.
- The current code on `main` (migration head 0050), checked line by line in `scheduler-gap-analysis.md`.
- The existing requirements (`ADM-SVS`, `ADM-SCH`, `ADM-CAP`, `ADM-CRW`, `ADM-CNC`, customer rules) and the 03 to 05 Nov 2026 owner decisions.

Rules followed:

- Each requirement has an ID. The prefix is `SCHR-` (scheduler rules). Groups: PAR (parameters), CFG (no hardcoding), HIER (rule hierarchy), HARD (hard constraints), EXT (exterior pass), INT (interior pass and entitlement), CUT (cutoff), WKE (weekend), ZONE (zones), BRK (break), OUT (outputs), DEF (deferral). IDs are never renumbered; a new ID goes at the end of its group.
- **Status** column:
  - **Owner**: the sheet states it (or the owner's note in the sheet table states it).
  - **Derived**: not stated, but needed to make a stated rule work, or taken from existing behaviour. Please check these.
  - **Open**: waits for an owner decision. None is open at v0.2: the owner answered all questions on 05-Nov-26 (section 13).
- Only functional requirements. Where the sheet says "configuration", the setting is listed in the configuration table and in group SCHR-PAR.
- Dates are `dd-Mon-yy`. Times are written as 24-hour `HH:MM` and stored as minutes after midnight, like the existing settings.
- Words: a cleaner is a crew member who is counted for capacity (a Member or a Manager; a Trainee adds no capacity, ADM-CAP-02). Exterior is Cleaning-External. Interior is Cleaning-Internal. A working day is a day the site is open (SCHR-PAR-02). The weekend is Saturday and Sunday (SCHR-PAR-10).

## Contents

1. Configuration table
2. Parameters (SCHR-PAR)
2a. No hardcoding (SCHR-CFG)
3. Rule hierarchy (SCHR-HIER) and how conflicts resolve
4. Hard constraints (SCHR-HARD)
5. Exterior pass, Pass A (SCHR-EXT)
6. Interior pass, Pass B, and entitlement accounting (SCHR-INT)
7. Cutoff policy (SCHR-CUT) and weekend handling (SCHR-WKE)
8. Zones (SCHR-ZONE)
9. Break (SCHR-BRK)
10. Outputs (SCHR-OUT)
11. Deferral at execution (SCHR-DEF)
12. Entitlement accounting, worked example
13. Owner decisions (05-Nov-26)

---

## 1. Configuration table

"Site" means one society (a Priveo site). Today the settings registry (`schedule.*` in `system_settings`) is global and the only per-site scheduling data is the working slots, so every "site" setting below needs a place to live (SCHR-PAR-01). "Existing" means the setting or table is already in the code and only its default, meaning or screen changes.

| Setting (proposed key) | Default | Scope | Edited by | New or existing | Extends | Where configured today (file or UI section) | Reuse or new |
|---|---|---|---|---|---|---|---|
| Weekly off weekday | Wednesday (weekday 2) closed for Exterior, Interior and Deep Spa | Site | Admin, Reference data, Working slots | Existing, default changes | `WorkingSlot.days` (a weekday with no slot is a day off, ADM-CAP-08). Seed default in `directory/defaults.py` and `directory/seed.py` gives all 7 days today | Site Setup, Reference data, Slots tab (`apps/web/src/pages/reference/SlotsTab.tsx`); table `working_slots` | Reuse (change seed default) |
| Working days | Mon, Tue, Thu, Fri, Sat, Sun | Site | Admin | Existing | Same working slots. Working days are the weekdays that have a slot | Same Slots tab | Reuse |
| `site.reporting_minute` | 05:00 (300) | Site default, crew override | Admin: Site Setup (default), Crew detail (override) | New | New site settings store. New nullable `SchedulingCrew.reporting_minute` | Not configured today. Crew hours: `apps/web/src/pages/crew/HoursEditor.tsx` | New site section plus new crew field |
| `site.first_job_minute` | 05:30 (330) | Site default, crew override | Same | New | Same. Becomes the earliest start the solver may use for a cleaner's first window of the day | Not configured today. Crew hours: HoursEditor | New site section plus new crew field |
| Exterior duration | 30 min | Global (all sites) | Admin: Reference data, Services | Existing, default changes | `DirectoryService.duration_minutes` (20 today) | Reference data, Services tab (`ServicesTab.tsx`); table `directory_services` | Reuse (change seeded value) |
| Interior duration | 30 min | Global | Same | Existing, default changes | Same (20 today) | Same Services tab | Reuse (change seeded value) |
| Combined visit | 60 min (sum of the two jobs, not a separate setting) | Derived | None | Derived | Shown in capacity maths only | Not a setting; sum of two durations | Reuse |
| `site.interior_earliest_minute` | 07:00 (420) | Site | Admin: Site Setup | New | Applied to Cleaning-Internal windows on every working day, weekday and weekend | Not configured today. Closest: Slots tab start of the Cleaning-Internal slot | New site section |
| `site.break_enabled` | On | Site default, crew override | Admin | New | New break rule table | Not configured today. Closest: extra working slots in HoursEditor | New site section plus new break dialog |
| `site.break_start_minute`, `site.break_end_minute` | 09:30 (570), 10:00 (600) | Site default; override by crew and by date range | Admin: Site Setup and Crew detail | New | New break override table with start date, end date, optional crew, optional times, on or off. Cues Today, Tomorrow, Date range | Not configured today | New site section plus new break dialog on Site Setup and Crew detail |
| `site.weekday_cutoff_hard` | On | Site | Admin | New | Applies to the strict days (working days that are not weekend days) | Not configured today. Default cutoff is in Settings, Schedule tab (`schedule.default_cutoff_time`, `settings_registry.py:62`) | New site section (cutoff policy) |
| `site.weekend_cutoff_flexible` | On | Site | Admin | New | Applies to the weekend days | Not configured today | New site section (cutoff policy) |
| `site.weekend_weekdays` | Saturday, Sunday | Site | Admin | New (Derived) | Decides which working days are "weekend" for the two cutoff settings and for Pass B | Not configured today | New site section (cutoff policy) |
| `schedule.interior_entitlement_per_week` | 1 | Global | Admin: Preferences | New | Interior services a plan gives for each service week | Not configured today. Settings page, Schedule tab lists every `schedule.*` registry key (`apps/web/src/pages/settings/SettingsPage.tsx:35`, `104-106`) | Reuse: new registry key, appears on the Schedule tab by itself |
| `schedule.service_week_start` | Monday (0) | Global | Admin: Preferences | New (Derived) | Separate from `schedule.week_start` (Sunday, the planning period) | Settings page, Schedule tab, next to `schedule.week_start` (`settings_registry.py:53`) | Reuse: new registry key |
| Crew home zone | None set (no restriction) | Crew, within a site | Admin: Crew detail | New | One nullable `home_zone_id` on the crew record (or a link table). `Zone` and `Vehicle.zone_id` exist | Zones: Reference data, Zones tab (`ZonesTab.tsx`). Crew detail has no zone field | Reuse Zones tab; new field on Crew detail |
| `site.cross_zone_help_allowed` | On | Site | Admin | New (Derived) | Off means a cleaner never serves a zone other than their home zone | Not configured today | New site section |
| Objective order and weights | Order of section 3, as seeded values | Global | Admin: Scheduling rules | New | Stored as configuration (`scheduler.objective_order`, `scheduler.weight_*`), seeded by migration; solver reads them. Editing asks for confirmation | Hardcoded in `scheduling/solver.py:16-18` | New: Scheduling rules section (admin-visible, edit with confirm) |
| Late-start, leave and sick exceptions | As today | Crew and date | Admin | Existing | `SchedulingCrewException`, unchanged | Crew detail, exceptions (`apps/web/src/pages/crew/`) | Reuse |
| Planning grid step | 5 min | Global | Admin: Scheduling rules | Existing in code (`solver.py:14`) | Registry/lookup layer | Hardcoded `STEP`, web `SNAP` in `Board.tsx:6` | New registry key `scheduler.grid_minutes` (Settings, Schedule tab) |
| Solver time limit and random seed | 10 s, seed 7 | Global | Admin: Scheduling rules | Existing in code (`solver.py:50`, `140`) | Registry/lookup layer | Hardcoded | New registry keys (Settings, Schedule tab) |
| Freeze hour, customer change hour, unfreeze code | 20, 21, `unfreeze` | Global | Admin: Settings | Existing | Registry/lookup layer | Settings, Schedule tab (`settings_registry.py:55-61`) | Reuse (remove the constants in `rules.py:12-15`) |
| Automatic planning time, retry minutes | none, 30 and 5 | Global | Admin | Existing, partly | Registry/lookup layer | `AutomaticPlanningSettings.tsx`, cron controls on the Scheduled jobs page; retry minutes hardcoded (`automatic.py:59`, `87`) | Reuse; retry minutes become registry keys |
| Could-not-complete / deferral reasons | As seeded | Global | Admin | Existing | Registry/lookup layer | Reference data (`directory/defaults.py:39-50`, table `cnc_reasons`) | Reuse |

Order in which a value is found for a cleaner on a day: crew override for that date, crew default, site value for that date (break only), site value, global default, built-in default.

---

## 2. Parameters (SCHR-PAR)

| ID | Requirement | Status |
|---|---|---|
| SCHR-PAR-01 | The scheduler reads its settings from one place that can hold a value for each site. A site that has no value of its own uses the global default, and then the built-in default in the configuration table. | Derived |
| SCHR-PAR-02 | Working days are Monday, Tuesday, Thursday, Friday, Saturday and Sunday. Wednesday is the weekly off: no Exterior and no Interior job is planned on it. Both are managed by configuration, through the site working slots (ADM-SVS-02): a weekday with no slot is a day off. | Owner |
| SCHR-PAR-03 | The weekly-off weekday is a site setting and defaults to Wednesday (owner, 05-Nov-26). It closes Exterior, Interior and Deep Spa. The default working slots of a new site leave that weekday out. Existing sites change only when the admin saves the change or the owner approves a data update. | Owner |
| SCHR-PAR-04 | Cleaners report at 05:00 and the first Exterior job starts at 05:30. These are two settings at site level, `reporting_minute` and `first_job_minute`. The crew screen shows the site values as the default for each cleaner. The admin can edit a value for one cleaner, which overrides the site value for that cleaner only. The reporting time is shown and recorded only. The earliest job start of a cleaner is the later of the first-job time and the start of the cleaner's window (owner, 05-Nov-26). | Owner |
| SCHR-PAR-05 | A cleaner with no override of their own follows the site value, including when the site value changes later. Clearing a cleaner's override returns them to the site value. | Derived |
| SCHR-PAR-06 | The job duration is 30 minutes for an Exterior and 30 minutes for an Interior. A visit with both takes 60 minutes of work, including movement between cars and zones. Duration stays an admin-editable service setting (ADM-SVS-09); the default changes from 20 to 30 minutes. The 5-minute board grid stays. Existing 20-minute jobs keep their length until they are planned again (owner, 05-Nov-26). | Owner |
| SCHR-PAR-07 | Deep Spa keeps its planning duration of 120 minutes. The sheet does not mention it. | Derived |
| SCHR-PAR-08 | The earliest start of an Interior job is 07:00 on every working day, weekdays and weekends, set by `interior_earliest_minute` at site level. | Owner |
| SCHR-PAR-09 | The break for all crew is 09:30 to 10:00 (30 minutes), managed by configuration. There is a site default, a crew override and a date-range override. The admin sets a range with the cues Today, Tomorrow or Date range. The most specific rule wins (SCHR-BRK-06). | Owner |
| SCHR-PAR-10 | The weekend is Saturday and Sunday. The setting `weekend_weekdays` holds them so that the cutoff rules (SCHR-CUT, SCHR-WKE) do not depend on fixed weekday numbers. | Derived |
| SCHR-PAR-11 | The customer cutoff has two settings: strict on weekdays (`weekday_cutoff_hard`, on) and flexible on the weekend (`weekend_cutoff_flexible`, on). Both are managed by configuration. | Owner |
| SCHR-PAR-12 | The interior entitlement is one Interior service for each service week, held in the setting `interior_entitlement_per_week` (default 1). The rule is written into the rule hierarchy (SCHR-HIER) and the accounting rules (SCHR-INT). | Owner |
| SCHR-PAR-13 | A service week runs Monday to Sunday. The start day is its own setting, `service_week_start`, separate from the planning period's week start, which is Sunday by default (ADM-SCH-09) (owner, 05-Nov-26). | Owner |
| SCHR-PAR-14 | The admin changes these settings in the web portal. Every change is recorded in the Audit trail with the admin and the time (ADM-SET-07). A change applies the next time a day is planned. A day that is already frozen is not replanned by a settings change. | Derived |
| SCHR-PAR-15 | The order and weights of the objectives in section 3 are configuration values, seeded with that order, readable in the admin portal and editable with a confirmation (see SCHR-CFG). | Owner |
| SCHR-PAR-16 | The weekly off applies to Exterior, Interior and Deep Spa alike (owner, 05-Nov-26). | Owner |

---

## 2a. No hardcoding (SCHR-CFG)

Owner instruction of 05-Nov-26: no rule, value or threshold is hardcoded in the scheduler.

| ID | Requirement | Status |
|---|---|---|
| SCHR-CFG-01 | No rule, configuration or value is hardcoded in the scheduler. This covers times, durations, the weekly-off day, reporting, first-job and Interior-earliest times, the break window, the cutoff policy, the service-week start, objective weights and priorities, zone rules, thresholds, grid step, solver limits and reason lists. Every one is read from admin configuration. | Owner |
| SCHR-CFG-02 | Every value is editable by the admin in the web portal. A value reuses an existing configuration place where one fits (Settings page, Reference data tabs, Crew detail, Automatic planning, Scheduled jobs). A new place is added only where none fits. The configuration table lists where each value lives. | Owner |
| SCHR-CFG-03 | Defaults are seeded by migration or by the seed tool into the configuration tables. Code constants are not defaults. The only values kept in code are the allowed ranges used to validate input. | Owner |
| SCHR-CFG-04 | The solver and the planner read every value through the lookup and settings layer (`directory/lookup.py`), never from a module constant. A missing value stops the run with a clear error and an alert; it is not replaced by a hidden default. | Owner and Derived |
| SCHR-CFG-05 | Every value is validated on save (type, range, and consistency such as break start before break end, first-job time not before reporting time, Interior-earliest not before first-job time). A refused value gives a message that says what to enter. | Owner and Derived |
| SCHR-CFG-06 | Every change is recorded in the Audit trail with the admin, the time, the old and the new value, and the site where it applies (ADM-SET-07). | Owner |
| SCHR-CFG-07 | A change applies from the next plan that is not frozen. It does not change a frozen schedule or jobs that have started, and it does not rewrite past days or past reports. | Owner |
| SCHR-CFG-08 | Each run records the values it used (a snapshot of the configuration), so a plan can be explained after a value has changed. | Derived |
| SCHR-CFG-09 | The existing constants listed in `scheduler-gap-analysis.md` ("Hardcoded values to remove") are moved into configuration and removed from the code. A test fails the build if a listed constant comes back. | Owner and Derived |
| SCHR-CFG-10 | New admin sections are added only for values with no current place: a Scheduling rules section in Site Setup (per-site values), a break dialog, and a home-zone field on Crew detail. Global values are new keys on the Schedule tab of the Settings page. | Derived |

---

## 3. Rule hierarchy (SCHR-HIER) and how conflicts resolve

This section is the order the scheduling job follows for one site and one day. A higher level always wins over a lower one. Inside a level, the numbered objectives are applied in order: an objective may only be improved if every objective above it keeps its best value (lexicographic order).

**Level 0. Inputs.** For the site and the day D:

- open(D): D's weekday has a working slot for the service. If not, no job of that service is planned.
- cleaners(D): active Members and Managers with working hours on D, after exceptions (Sick, Leave, Late start). Each has a first-job time, a break (or none), and owned zones.
- cars(D): vehicles with an Active subscription that has started, not skipped or paused on D (existing rule, `build_demand`).
- cutoff(car, D): the finish-by time of the car for D (the date's override, else the subscription's default), and its mode on D: hard on a strict day, flexible on a weekend day.
- ledger: the Interior entitlements of the site that are not yet fulfilled, each with its service week (section 6).
- interior_earliest, break rules, zone ownership, durations.

**Level 1. Hard constraints.** Never broken. If they make a job impossible, the job is left unassigned and reported (SCHR-OUT-03). See SCHR-HARD.

**Level 2. Mandatory exterior coverage (Pass A).** One Exterior for every active car on every working day, placed before any Interior. Result: the set of Exterior jobs placed, with the shortfall reported.

**Level 3. Ordered objectives.** Higher first.

Pass A (Exterior), after Level 2 coverage is maximal:

1. Zones: fill each cleaner's home zone first, then take jobs of other zones into spare capacity, recording the reason (SCHR-ZONE-03, SCHR-ZONE-04).
2. Weekend cutoffs: on a weekend day, as few late jobs as possible (Derived, so that item 3 does not break cutoffs, sheet rule 06).
3. Usable early capacity: as many free cleaner minutes as possible from `interior_earliest` onward that a pending Interior could use before its cutoff, and free minutes between first-job time and `interior_earliest` kept for Exterior or onboarding (SCHR-EXT-05).
4. Cleaner break kept (SCHR-BRK).
5. Fewer zone switches in a cleaner's day.
6. Earlier start times.
7. A fixed random seed, so the same input gives the same plan.

Pass B (Interior), run after Pass A, with every Pass A placement fixed:

1. Older service weeks first (FIFO by service week, then by how long the car has waited, SCHR-INT-12), then the current service week.
2. As many Interiors as possible on weekdays, before a remainder is given to the weekend. Days are filled in date order within the period.
3. Zones, as in Pass A.
4. On the weekend, as few late jobs as possible.
5. Fewer zone switches, earlier start, fixed seed.
6. Break: an Interior never overlaps a kept break. This is a hard rule in Pass B (the break wins over an Interior, SCHR-BRK-02).

**Level 4. Outputs.** The daily cleaner view, the weekly summary and the exception report (SCHR-OUT).

**How conflicts resolve.**

| Conflict | Result |
|---|---|
| Exterior coverage against a hard rule (shift, overlap, first-job time, weekday cutoff, weekly off) | The hard rule wins. The Exterior is left unassigned and reported with the reason and the shortfall. |
| Exterior coverage against the break | Coverage wins. The break is dropped and flagged as missed, only when no other plan places the Exterior. |
| Weekday cutoff against the break | The cutoff wins. The break is dropped and flagged. |
| Weekday cutoff against an Interior | The cutoff wins. The Interior is deferred (stays pending) and reported. It never displaces an Exterior. |
| Break against an Interior | The break wins. The Interior is deferred. |
| Home zone against a cutoff or coverage | Coverage and weekday cutoffs win: a cleaner may take another zone's job into spare capacity, and cross-zone work never pushes a home-zone job past its cutoff. The reason is recorded. |
| Home zone against a preferred free slot | The home zone is filled first. A cleaner never crosses zones only to create a free slot. |
| Early free capacity against coverage or a cutoff | Coverage and cutoffs win. Free capacity is never created by breaking them. |
| Early free capacity against an eligible Interior | The Interior takes the free slot. A slot is never kept idle on purpose. |
| Older service week against a newer one | The older week is placed first. A newer week is placed only in what is left. |
| Weekend cutoff against the break | The break wins. The Interior runs after the break and is flagged late (owner, 05-Nov-26). |

**Worked examples: weekend cutoff, Exterior first, break.** Customer: Hyundai Creta, Customer cutoff 08:30, Exterior 30 minutes, Interior 30 minutes. They illustrate SCHR-WKE-01 to 03, SCHR-WKE-05, SCHR-CUT-01 to 03, SCHR-BRK-02, SCHR-HIER-05 and SCHR-HIER-07. They are test scenarios S34, S35 and S36 in the test plan.

| Case | Day | Plan | Result |
|---|---|---|---|
| 1 | Saturday | Exterior 08:00 to 08:30, Interior 08:30 to 09:00 | Allowed. On a weekend the cutoff is flexible for Exterior and Interior; the Interior ends after 08:30, is flagged late, and the planner still tries to keep lateness as small as it can. |
| 1b | Thursday (weekday counterpart) | Same plan | Not allowed. Both jobs must finish by 08:30. The Interior is not planned at 08:30 to 09:00; it is deferred or left unassigned with the reason "Customer cutoff" and reported. |
| 2 | Saturday, all cleaners busy with other mandatory Exteriors, earliest slot 09:00 | Exterior 09:00 to 09:30 | Allowed (weekend, car available, inside the cleaner's shift). |
| 2a | Same, the cleaner's 09:30 to 10:00 break is not due | Interior 09:30 to 10:00 | Allowed. |
| 2b | Same, the break is due | Interior in a later slot | The break wins over the Interior. |

"Exterior first" in these examples means the planner allocates an Exterior for every car before it assigns any Interior. It is a planning sequence, not an execution barrier: a cleaner who has finished their own Exteriors may start an Interior while another cleaner is still working on Exteriors.

| ID | Requirement | Status |
|---|---|---|
| SCHR-HIER-01 | The scheduler plans one site and one day at a time in this order: inputs, hard constraints, Pass A (Exterior), Pass B (Interior), outputs. Days of a period are planned in date order, so the entitlement ledger left by one day is the input of the next. | Derived |
| SCHR-HIER-02 | Hard constraints are never broken by any objective. A job that cannot be placed without breaking one is left unassigned and reported, never hidden. | Owner |
| SCHR-HIER-03 | The objectives of Pass A and Pass B are applied in the order of section 3. An objective can change the plan only among plans that keep every higher objective at its best value. | Derived |
| SCHR-HIER-04 | The priority order in the sheet is: complete mandatory daily Exteriors; preserve zone ownership; prefer usable early capacity in the Exterior pass; protect the 09:30 to 10:00 break ahead of Interior cleaning; maximise weekday Interiors; on weekends plan all Exteriors first and then Interiors, oldest service week first; prefer to meet weekend cutoffs. | Owner |
| SCHR-HIER-05 | Where the sheet's list puts "prefer meeting weekend cutoffs" last but rule 06 says free capacity must not be created by violating cutoffs, weekend lateness is minimised above the early-capacity objective in Pass A. On a weekend the break wins over the cutoff: an Interior runs after the break and is flagged late against the weekend cutoff. Exterior still comes first (owner, 05-Nov-26). | Owner and Derived |
| SCHR-HIER-06 | Tie-breaks, in order: fewer cross-zone assignments, fewer zone switches in a cleaner's day, earlier start, a stable order by vehicle creation date and ID, then the fixed random seed. | Derived |
| SCHR-HIER-07 | Pass A and Pass B are two separate solves. Pass B receives Pass A's placements as fixed jobs and fills the gaps. "Exterior first" is a planning order only: a cleaner who has finished their own Exteriors may start an assigned Interior while another cleaner still works on Exteriors (SCHR-INT-08). | Owner |
| SCHR-HIER-08 | Jobs placed by hand and jobs already frozen stay where they are and take up the cleaner's time in both passes, as today (ADM-SCH-14, ADM-SCH-27). The admin may place a job against any rule; the screen warns and each breach is flagged in the exception report. The scheduler itself never breaks a hard constraint (owner, 05-Nov-26). A hand move that overlaps another job is refused, not warned (ADM-SCH-43). | Owner and Derived |

---

## 4. Hard constraints (SCHR-HARD)

| ID | Requirement | Status |
|---|---|---|
| SCHR-HARD-01 | Before assigning, the scheduler checks each cleaner's availability for the day and uses only available cleaners (working hours, Sick, Leave, Late start, role). | Owner |
| SCHR-HARD-02 | A cleaner's own shift end is never passed. A job must end inside one of the cleaner's windows. | Owner |
| SCHR-HARD-03 | A cleaner is never given two overlapping jobs. | Owner |
| SCHR-HARD-04 | No job starts before the cleaner's first-job time (05:30 by default). Cleaners report at 05:00, which is not a start time for jobs. | Owner |
| SCHR-HARD-05 | No Interior starts before the Interior-earliest time (07:00 by default), on any day. | Owner |
| SCHR-HARD-06 | Every Exterior and every Interior takes exactly its set duration (30 minutes by default). No travel minutes are added for movement between cars or zones. | Owner |
| SCHR-HARD-07 | No Exterior or Interior is planned on a weekly off day. | Owner |
| SCHR-HARD-08 | On a strict day (Monday, Tuesday, Thursday, Friday by default), no Exterior and no Interior ends after the car's cutoff time. | Owner |
| SCHR-HARD-09 | Every active car needs one Exterior on every working day. If that is not possible, the shortfall is reported and not hidden. | Owner |
| SCHR-HARD-10 | At most one Interior is planned or completed against the same service week of a car. | Owner |
| SCHR-HARD-11 | At most one Interior is planned for a car on a day. Two Interiors in one calendar week are allowed only on separate days, each for a different service week. | Owner |
| SCHR-HARD-12 | One car is never worked on by two cleaners at the same time. This already holds today. | Derived |
| SCHR-HARD-13 | A job whose cleaner has no window that fits its duration is reported as unassigned with the reason (existing behaviour, ADM-SCH-08). | Derived |

---

## 5. Exterior pass, Pass A (SCHR-EXT)

| ID | Requirement | Status |
|---|---|---|
| SCHR-EXT-01 | Every active car has one Exterior assignment on each working day. | Owner |
| SCHR-EXT-02 | Each Exterior takes a fixed 30-minute slot that includes movement between cars and zones. | Owner |
| SCHR-EXT-03 | All Exterior jobs of the day are allocated before any Interior is allocated, including on the weekend. | Owner |
| SCHR-EXT-04 | Exterior has the highest service priority. When resources make full coverage impossible, the scheduler places as many Exteriors as it can, and the output names every unassigned car, the reason and the shortfall in cars and minutes. | Owner |
| SCHR-EXT-05 | Among plans that cover the same Exteriors, the scheduler prefers the one that leaves the most usable early free capacity. "Usable" means free cleaner time that is not before the Interior-earliest time and that a pending Interior could use before its cutoff on a weekday. Free time at the end of the shift counts less than free time earlier. | Owner and Derived |
| SCHR-EXT-06 | Early free capacity is never made by breaking a cutoff, by leaving Exterior coverage short, or by clearly increasing zone changes. | Owner |
| SCHR-EXT-07 | A free slot is never kept idle on purpose. An eligible Interior takes a suitable free slot. | Owner |
| SCHR-EXT-08 | The time between the first-job time and the Interior-earliest time (05:30 to 07:00 by default) is for Exterior jobs or customer onboarding. From the Interior-earliest time, a free slot can be used for an Interior as well, subject to keys, cutoff and capacity. | Owner |
| SCHR-EXT-09 | Free capacity in the 05:30 to 07:00 band that stays free is shown in capacity as available for onboarding. The scheduler does not hold it back from Pass B and does not reserve it. | Derived |
| SCHR-EXT-10 | The Exterior pass minimises zone changes among equally good plans. | Owner |
| SCHR-EXT-11 | A subscription with a Weekly or Cycle pattern (ADM-SCH-41) can give a car fewer than six Exteriors a week. The entitlement model replaces the Custom interior rotation; patterns that name Interior days feed the preference only (owner, 05-Nov-26). The exact handling of the Exterior-only days of a pattern is Derived: the pattern is kept. | Owner and Derived |
| SCHR-EXT-12 | An Exterior that was not done is not carried forward. The next working day's Exterior covers it, as ADM-CNC-03 says. | Derived |

---

## 6. Interior pass, Pass B, and entitlement accounting (SCHR-INT)

| ID | Requirement | Status |
|---|---|---|
| SCHR-INT-01 | An Interior is planned for a car only when the car has a pending Interior entitlement for a service week up to and including the service week of the day planned. The weekday on which the Interior is planned does not have to match the customer's interior care day. | Owner and Derived |
| SCHR-INT-02 | Each Interior takes exactly 30 minutes, including movement between cars or zones. | Owner |
| SCHR-INT-03 | No Interior starts before 07:00 on any day, including the weekend, because customer keys may not be reachable earlier. | Owner |
| SCHR-INT-04 | A visit that has both an Exterior and an Interior occupies 60 minutes of work. The two 30-minute jobs may follow one another or be apart, and may be done by different cleaners. | Owner |
| SCHR-INT-05 | The customer's interior care day (ONB-18) is a preference only and does not bind the scheduler. It may be used as a tie-break among equal plans. Exceptional customer requests are handled by hand by the admin. The gap rule for the preferred day is SCHR-INT-27. | Owner and Derived |
| SCHR-INT-06 | The default entitlement is one Interior service for each service week. A second Interior is never planned against the same service week. | Owner |
| SCHR-INT-07 | Pass B starts only after all Exterior jobs of the day are allocated. It looks at the gaps of 30 minutes or more that start no earlier than 07:00. | Owner |
| SCHR-INT-08 | Exterior first is a planning sequence, not an execution barrier. An Interior can be assigned to a cleaner who is free while others are still working on Exteriors. | Owner |
| SCHR-INT-09 | Pass B respects weekday cutoffs, kept breaks and the existing Exterior assignments. | Owner |
| SCHR-INT-10 | The scheduler places as many weekday Interiors as it can. What cannot be placed on weekdays is offered to Saturday and Sunday, after those days' Exteriors are assigned. | Owner |
| SCHR-INT-11 | Every Interior carries an explicit service week, stored as the first date of the week. The service week is kept until the Interior is actually done. | Owner |
| SCHR-INT-12 | Pass B orders eligible entitlements by service week, oldest first (first in, first out), then by the current week. Among entitlements of the same week, the one that has waited longest goes first, then the one with the tighter weekday cutoff, then the stable order of SCHR-HIER-06. | Owner and Derived |
| SCHR-INT-13 | If the Interior of week 1 is not done by the last day of week 1, it carries into week 2 with a higher priority than the new Interior of week 2. | Owner |
| SCHR-INT-14 | When the overdue Interior is done in week 2, the completion is recorded against week 1, not week 2. | Owner |
| SCHR-INT-15 | Week 2's entitlement is never marked complete because week 1's overdue Interior was done. | Owner |
| SCHR-INT-16 | An overdue Interior keeps its original service week until it is done. Older pending weeks are processed first. | Owner |
| SCHR-INT-17 | Reports show, for each Interior, the original service week, the number of overdue days, and the completion date. | Owner |
| SCHR-INT-18 | More than one physical Interior may be done for a car in the same calendar week (a catch-up week), only on separate days, where each fulfils a different service week and capacity exists. The worked example is in section 12. | Owner |
| SCHR-INT-19 | A new entitlement is created for each Active subscription whose plan includes Interior care, for each service week from the week of its first service date. Creation is repeatable: running it twice makes no second row. | Derived |
| SCHR-INT-20 | Every service week that a subscription touches owes one Interior, even a part week at the start or the end (owner, 05-Nov-26). A plan change keeps the week's entitlement if the new plan includes Interior. | Owner and Derived |
| SCHR-INT-21 | An operational miss (car, keys, capacity, operations skip) is owed and carries forward. A service week that is fully paused is waived. A one-day customer skip leaves the entitlement pending until the week ends (owner, 05-Nov-26). This replaces customer business rule 2 and the last sentence of ADM-SVS-01 ("lost and not made up"). | Owner |
| SCHR-INT-22 | An Interior bought as an extra (the Extra interior cleaning add-on) or a Deep Spa does not use up the weekly entitlement. | Derived |
| SCHR-INT-23 | A plan whose services do not include Interior care has no entitlement and gets no Interior. | Derived |
| SCHR-INT-24 | An Interior placed by hand is counted against the oldest pending service week of the car, unless the admin picks another week. | Derived |
| SCHR-INT-25 | The entitlement model replaces the Custom interior care day rotation (ADM-SUB-10, parked on 03-Nov-26). A Custom subscription is a normal case; its notes stay informational (owner, 05-Nov-26). | Owner |
| SCHR-INT-26 | A Weekly or Cycle pattern (ADM-SCH-41) that names Interior days feeds the car's preferred days (a tie-break, SCHR-INT-05). It does not override the entitlement model. | Derived |
| SCHR-INT-27 | If the gap after the car's preferred Interior day is up to 2 days, the preferred day is kept. If the gap is larger, the Interior is held as optional: the screen shows "Preferred Interior day moved: last Interior on <date>" and the Interior goes to Unscheduled. The 2-day threshold is Derived (8 Nov 2026). | Derived |
| SCHR-INT-28 | If no Interior is planned in the car's plan week, the Interior is held as optional, as SCHR-INT-27 says (built, 8 Nov 2026). Whether the car should keep its preferred day instead is open (admin file, section 13, question 2). | Open |

---

## 7. Cutoff policy (SCHR-CUT) and weekend handling (SCHR-WKE)

Three different times are called "cutoff" in the product. In this file: the **Customer cutoff** is the time by which a car's clean must be finished (ONB-16, `Subscription.cutoff_time`, `Job.finish_by_minute`). The **Freeze** is 8 PM the day before a schedule starts (ADM-SCH-25). The **9 PM rule** is 9 PM the day before a date (SCHED-01). Only the Customer cutoff is used by the scheduler rules below. The words "service cutoff", "cutoff" and "weekday cutoff" elsewhere in this file mean the Customer cutoff.

| ID | Requirement | Status |
|---|---|---|
| SCHR-CUT-01 | On Monday, Tuesday, Thursday and Friday the service cutoff is a hard completion deadline for both Exterior and Interior. | Owner |
| SCHR-CUT-02 | A job is never scheduled to finish after its car's cutoff on those days. | Owner |
| SCHR-CUT-03 | If an Interior cannot fit before the cutoff, it is deferred and stays pending. This never costs an Exterior its place. | Owner |
| SCHR-CUT-04 | If an Exterior cannot fit before the weekday cutoff, it is left unassigned and reported with the reason and the cutoff time. It is not placed late (owner, 05-Nov-26). | Owner |
| SCHR-CUT-05 | An admin who places a job by hand after a weekday cutoff is warned and the job is marked Late, as in ADM-SCH-07. The admin may go ahead; the breach is flagged in the exception report (owner, 05-Nov-26). | Owner |
| SCHR-CUT-06 | The three cutoffs are named in screens and reports as Customer cutoff (the scheduler's deadline), Freeze (8 PM, ADM-SCH-25) and 9 PM rule (SCHED-01) (owner, 05-Nov-26). | Owner |
| SCHR-CUT-07 | The customer can still choose any cutoff in 30-minute steps (ONB-16). A cutoff earlier than the first-job time plus the duration cannot be met on a strict day; the car is left unassigned and reported (SCHR-CUT-04). The app does not warn or limit the choice. | Derived |
| SCHR-CUT-08 | The late-assignment rule after a freeze (ADM-SCH-27, earliest time before the cutoff) stays and is consistent with the hard weekday cutoff. | Derived |
| SCHR-WKE-01 | On Saturday and Sunday the service cutoff is flexible for Exterior and Interior: the scheduler prefers to meet it when the car is available. | Owner |
| SCHR-WKE-02 | The scheduler finishes all weekend Exteriors first, then gives the remaining capacity to Interiors. | Owner |
| SCHR-WKE-03 | A weekend Exterior or Interior may end after the normal cutoff only if the vehicle is physically available. The job must still end inside the assigned cleaner's shift. | Owner |
| SCHR-WKE-04 | The scheduler does not know whether a car is physically there at planning time (no such data exists). It assumes the car is available. An unavailable car is found at execution and handled by deferral (SCHR-DEF). | Derived |
| SCHR-WKE-05 | Eligible outstanding Interiors are allocated on Saturday and Sunday after the weekend Exteriors, oldest service week first. | Owner |
| SCHR-WKE-06 | Weekend lateness against a cutoff is reported in the exception report (SCHR-OUT-03). | Owner |

---

## 8. Zones (SCHR-ZONE)

| ID | Requirement | Status |
|---|---|---|
| SCHR-ZONE-01 | Each society has several zones and each vehicle has one zone. Each cleaner has one home zone, set by the admin. The scheduler fills the cleaner's home zone first (owner, 05-Nov-26). | Owner |
| SCHR-ZONE-02 | The scheduler minimises the number of zone switches in a cleaner's day. | Owner |
| SCHR-ZONE-03 | After the home-zone jobs are placed, a cleaner may take jobs from other zones into spare capacity. This holds for both Exterior and Interior jobs. It replaces the sheet's wording "only when the zone owner cannot" (owner, 05-Nov-26). | Owner |
| SCHR-ZONE-04 | Before a cross-zone assignment the scheduler checks the cutoff, the cleaner's spare capacity and the weekly Interior requirement. A cleaner does not cross zones only to create a preferred free slot, and a cross-zone job never pushes a home-zone job past its cutoff. | Owner and Derived |
| SCHR-ZONE-05 | Movement across zones is part of the fixed 30-minute slot. No extra travel minutes are added. | Owner |
| SCHR-ZONE-06 | The reason for each cross-zone assignment is recorded on the job. Reasons: home-zone cleaner absent, home zone full, spare capacity used, needed to meet a cutoff or the weekly Interior. | Owner and Derived |
| SCHR-ZONE-07 | The admin sets one home zone for each cleaner on the crew screen. Several cleaners may share a home zone. A zone with no cleaner is served entirely as cross-zone work. | Owner and Derived |
| SCHR-ZONE-08 | A car with no zone (`Vehicle.zone_id` empty) is served by any cleaner of the site and never counts as cross-zone. | Derived |
| SCHR-ZONE-09 | Only Members and Managers have a home zone. A Trainee follows the paired Member's jobs and the Member's home zone (CRW-SCH-10). | Derived |
| SCHR-ZONE-10 | A zone switch is two jobs in a row in a cleaner's day that are in different zones. A cross-zone assignment is a job in a zone other than the cleaner's home zone. | Derived |
| SCHR-ZONE-11 | A site where no cleaner has a home zone plans as today: no zone preference and no cross-zone records. | Derived |

---

## 9. Break (SCHR-BRK)

| ID | Requirement | Status |
|---|---|---|
| SCHR-BRK-01 | The scheduler tries to give each cleaner one continuous 30-minute break from 09:30 to 10:00 on each working day. | Owner |
| SCHR-BRK-02 | If the break conflicts with an Interior, the break wins and the Interior is deferred. | Owner |
| SCHR-BRK-03 | Mandatory Exterior coverage and hard weekday cutoffs win over the break when there is no other feasible plan. | Owner |
| SCHR-BRK-04 | Every missed break is flagged in the output with the cleaner, the date and the reason. | Owner |
| SCHR-BRK-05 | The admin can change the break for a date range (start date, end date, new times, or no break), and picks Today, Tomorrow or Date range in the screen. | Owner |
| SCHR-BRK-06 | The site has the default break (09:30 to 10:00). A crew override and a date-range override can apply to the whole site or to one cleaner. The most specific rule wins: date and crew, then date, then crew, then site (owner, 05-Nov-26). | Owner |
| SCHR-BRK-07 | A cleaner whose window on that day does not cover the break time (a late start after 10:00, or a shift that ends before 09:30) has no break and no missed-break flag. | Derived |
| SCHR-BRK-08 | The break is not counted as capacity. Capacity for a day is the cleaner's windows minus the break. | Derived |
| SCHR-BRK-09 | The break is shown in the crew day and on the Board as a block that cannot take a job. | Derived |
| SCHR-BRK-10 | A change to a break for a date already frozen applies only to jobs that have not started and is recorded in the Audit trail. | Derived |

---

## 10. Outputs (SCHR-OUT)

| ID | Requirement | Status |
|---|---|---|
| SCHR-OUT-01 | The daily cleaner-wise view shows, for each cleaner: car ID, zone, type (Exterior or Interior), scheduled start and end, the car's cutoff, the break, free slots, any key or car availability exception, and any cross-zone assistance with its reason. | Owner |
| SCHR-OUT-02 | The weekly summary shows: completed against mandatory Exteriors; Interiors grouped by original service week and by actual completion date; weekday and weekend completions; catch-up services; carryover; missed breaks. | Owner |
| SCHR-OUT-03 | The exception report shows: unassigned mandatory Exteriors; pending or deferred Interiors; unavailable keys or cars; cross-zone triggers; shift or cutoff infeasibility; missed breaks. | Owner |
| SCHR-OUT-04 | Every unassigned job carries a reason from a fixed list (no cleaner, shift too short, weekday cutoff, weekly off, capacity short, break kept, Interior before 07:00, entitlement already used). | Derived |
| SCHR-OUT-05 | The reports are shown in the web portal on the Schedule page, for a chosen day or week. They are computed from jobs, the entitlement ledger and the recorded reasons; no separate copy of the numbers is stored. | Derived |
| SCHR-OUT-06 | The weekly summary can be exported as a file. | Derived |
| SCHR-OUT-07 | A run summary (placed, unscheduled, late) is extended with the counts of unassigned Exteriors, deferred Interiors, cross-zone assignments and missed breaks, and the run is recorded in the schedule history (ADM-SCH-19). | Derived |

---

## 11. Deferral at execution (SCHR-DEF)

| ID | Requirement | Status |
|---|---|---|
| SCHR-DEF-01 | At execution, if the car or the keys are not available, the service is marked deferred with a reason. A job that was not done is never marked completed. | Owner |
| SCHR-DEF-02 | A deferred service is tried again in the next feasible slot. | Owner |
| SCHR-DEF-03 | A deferred Interior goes back to pending on its entitlement, with its original service week, and is planned again with the priority of SCHR-INT-12. | Derived |
| SCHR-DEF-04 | The deferral reasons come from configuration (the could-not-complete reasons list, ADM-CNC-01), which the owner will extend. No change in this document (owner, 05-Nov-26). | Owner |
| SCHR-DEF-05 | Both, by case. When the key or the car is not available, the job takes the new Deferred state and the scheduler plans it again (SCHR-DEF-02). On a partial completion, ADM-CNC-10 stays: the admin or a Manager decides, and the missed Interior is rescheduled for the next day only (owner, 05-Nov-26). | Owner |
| SCHR-DEF-06 | A pending Interior does not expire. It stays until it is done (SCHR-INT-16). | Owner |

---

## 12. Entitlement accounting, worked example

Service week 1 is Monday 02-Nov-26 to Sunday 08-Nov-26. Service week 2 is Monday 09-Nov-26 to Sunday 15-Nov-26. Wednesday (04-Nov-26 and 11-Nov-26) is off.

| Date | What happens | Ledger, week 1 | Ledger, week 2 |
|---|---|---|---|
| Mon 02-Nov to Sun 08-Nov | The week-1 Interior is planned but missed (for example no keys, or no capacity). | Pending, overdue from 09-Nov | Not yet created |
| Mon 09-Nov | Week 2 begins. The week-1 entitlement is overdue (1 day) and goes first in Pass B. It is done on Monday. | Completed on 09-Nov (credited to week 1) | Pending |
| Mon 09-Nov | The same car gets no second Interior on this day (one Interior per car per day). | | |
| Thu 12-Nov | The week-2 Interior is planned and done, if time and car and key availability allow. | | Completed on 12-Nov |

The two cleans are two physical visits on separate days, each counted against a different service week. A report for week 1 shows: original week 02-Nov-26, overdue days 1, completion date 09-Nov-26. A report for week 2 shows its own completion date 12-Nov-26.

Ledger states: **Pending** (owed, not yet planned), **Planned** (a job exists), **Completed** (with the job and the date), **Waived** (not owed, SCHR-INT-21), **Cancelled** (the subscription ended). A deferral returns Planned to Pending and keeps the service week.

---

## 13. Owner decisions (5-Nov-26)

Answered by the owner on 05-Nov-26 in this session. The SCHR- rows that depend on these answers were updated in v0.2.

| # | Question | Owner decision | Rows affected |
|---|---|---|---|
| 1 | Wednesday off against "no rest day" | Site setting, weekly-off weekday defaults to Wednesday. The sheet overrides the earlier decision. Exterior, Interior and Deep Spa are all off. Change ADM-SVS-05, customer business rule 1, admin rule 4, PAY-02 wording. | SCHR-PAR-03, SCHR-PAR-16 |
| 2 | Carry-forward against "Interior skipped is lost" | Operational misses are owed and carry forward. A fully paused week is waived. A one-day customer skip stays pending until the week ends. Change customer business rule 2 and ADM-SVS-01. | SCHR-INT-21 |
| 3 | Service week | Monday to Sunday, as its own setting, separate from the planning period week start. | SCHR-PAR-13 |
| 4 | Duration | 30 minutes default for Exterior and Interior, still editable by admin. 5-minute board grid stays. Existing 20-minute jobs keep their length until replanned. | SCHR-PAR duration rows |
| 5 | Break scope | Site default plus crew override, plus date-range override. Most specific wins: date and crew, date, crew, site. | SCHR-BRK-06 |
| 6 | Weekday cutoff earlier than any feasible time | Leave the car unassigned and report it. | SCHR-CUT-04 |
| 7 | Zone ownership | Each society has several zones and each vehicle has one zone. Each crew member has one home zone, set by admin. The scheduler fills the home zone first, then takes jobs from other zones into spare capacity. This replaces the sheet's "only when the zone owner cannot" wording. The cross-zone reason is still recorded. | SCHR-ZONE rows, SCHR-HIER |
| 8 | Custom interior day (ADM-SUB-10) | The entitlement model replaces the rotation. Custom becomes a normal case and the notes stay informational. | SCHR-INT-25, SCHR-INT-26, SCHR-EXT-11 |
| 9 | Weekend: break against cutoff | The break wins. The Interior runs after the break and is flagged late against the weekend cutoff. Exterior still comes first. | SCHR-HIER-05 |
| 10 | Admin hand placement | Warn only. The admin may override every rule. Each breach is flagged in the exception report. | SCHR-HIER-08, SCHR-CUT-05 |
| 11 | First and last week of a subscription | Every service week the subscription touches owes one Interior, even a part week. | SCHR-INT-20 |
| 12 | Deferral against ADM-CNC-10 | Both, by case. Key or car unavailable uses the new Deferred state and replanning. Partial completion keeps the next-day rule. | SCHR-DEF-05 |
| 13 | Names of the three cutoffs | Customer cutoff (the scheduler's deadline), Freeze (8 PM, ADM-SCH-25), 9 PM rule (SCHED-01). | Terminology section |
| 14 | Reporting time against working hours | Reporting time is shown and recorded. The earliest job start is the later of the first-job time and the start of the cleaner's window. | SCHR-PAR-04 |
| 15 | Capacity | Report the shortfall only. Unassigned exteriors and the shortfall go in the exception report. | SCHR-OUT rows |
| 16 | Deferral reasons | Owner: these will be added in configuration. No change in this document. | SCHR-DEF-04 |

Nothing is open from the original 16 questions. The hand-placement decision (10) makes the hard constraints advisory for admins only; the scheduler itself never breaks them.

Open from 8 Nov 2026 (admin file, section 13, questions 1 and 2): what "Earliest" in Site Setup controls, and the no-Interior-in-the-week case (SCHR-INT-28).
