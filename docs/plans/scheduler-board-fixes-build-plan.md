# Scheduler board fixes: build plan

Version 1.1, 9-Nov-26 (owner confirmed the open points: shifted cards get By hand; sync is same browser only). Backup plan for a build that a coding agent (or a team of agents) can follow without the chat history.

Read first, in this order:

1. `CLAUDE.md` (repo root): repo rules, commands, merge rule.
2. `docs/reqs/owner-decisions-2026-11-09.md`: the owner's answers. Section 4 of this plan repeats them.
3. `docs/reqs/admin-functional-requirements.md`: the requirement IDs (ADM-SCH-*, ADM-CAP-*, ADM-SVS-*, ADM-CRW-*, ADM-OPS-*) that these items change.
4. `docs/design/scheduler-board-redesign.md` and `docs/design/admin-portal-ui-review.md`: board layout rules.

Code pointers below come from a read-only planning pass. They are starting points, not facts. Verify each file and line before editing.

---

## 1. Goal

Make the admin scheduler board behave like a Kanban board (smooth drag, instant sync, multi-select), fix four scheduler bugs (counters, "By hand" labels, re-planning, unscheduled cards not picked up), add job-card PDFs and a completion-status queue, make crew roles and working slots date-bound, and tidy several screens.

Out of scope: prod deployment. The build ends at a merge to `main`, which deploys to **test** only. Prod is a separate release.

---

## 2. Status of the codebase (9-Nov-26)

- Migration head: `0055` (`services/api/migrations/versions/20261109_0055_cutoff_driven_objectives.py`). CLAUDE.md still says `0039`: fix CLAUDE.md as part of the docs step, not in a feature branch.
- Focus mode and own-tab mode both render the same `CardBoard` component. Drag works in both today, but only via native HTML5 drag and drop.
- Hand locks, the Operations "Scheduled work" queue, the Table view and optimistic moves already exist.
- Sync today: a 30-second poll, plus a refetch on window focus (`apps/web/src/api/queryDefaults.ts`).
- Timeline is currently view-only (requirement ADM-SCH-33, 5-Nov redesign). Owner has reversed this (decision 6).
- A card `manual` flag already exists in the scheduler. The bugs below come from how it is set and cleared.

---

## 3. Owner decisions (binding)

| # | Topic | Decision |
|---|---|---|
| 1 | P1-1, investigate the 10-Nov INT jobs on prod | Removed. Do not build or investigate. |
| 2 | Re-plan cards that were taken off by hand | Yes, they must be re-planned. |
| 3 | Allowed completion statuses (P1-3) | Use the same statuses the Crew app already uses. Read the crew-side logic (`set_job_status` in `services/api/app/scheduling/service.py`, and the crew routes) and reuse those exact values. Do not invent new ones. |
| 4 | Drag and drop | No confirmation dialog on any drop. Sync must be instant. |
| 5 | Insertion (P0-5) | Dragged card goes between two cards, to the top, or to the bottom. Cards in its way shift to make space. Every shifted card is marked "By hand" (confirmed 9-Nov-26). Overlaps are refused. Late placements (after cutoff) are allowed. A drop that crosses crew hours or service hours shows a warning and is allowed, shown in red. |
| 6 | Timeline editable (P0-6) | Yes, the timeline is editable now. It was view-only before this decision. |
| 7 | Temporary crew role (P2-4) | Past runs are not affected. A temporary role changes scheduling only for the dates it covers, and only for days not yet run. |
| 8 | Working-slot exceptions (P3-3) | An exception beats the weekly-off rule for its dates. The weekly-off rule itself (from site working hours) stays as the default. Exceptions apply only on their own dates. Nothing hard-coded. |
| 9 | Sync scope (P0-9) | Same browser only for this build. Cross-device push is a later job. |
| 10 | Timeline snap (P0-6) | 5 minutes. |
| 11 | Pairing during a temporary role (P2-4) | Pairing rules unchanged. |

Confirmed on 9-Nov-26 after the first draft: shifted cards get "By hand"; instant sync is same browser only; timeline snap is 5 minutes; a temporary role does not change the pairing rules. Decisions 9 to 11 in the table above record these.

## 4. Backlog (IDs are used by every later section)

Each item lists the acceptance check that must pass before the item is done.

### P0 (drag and board)

**P0-1 Smooth drag engine.** Replace the native HTML5 drag in the board with a drag engine that shows a ghost card, shifts neighbours live, and snaps on drop. Keep optimistic moves with rollback when the server refuses. The engine is shared by every view and every later drag item.
- Done when: a card can be dragged in Cards (standard, compact and detailed views), Focus and own tab; the neighbours move while dragging; a refused drop returns the card to its origin with a message.

**P0-5 Insert between two cards.** A drop between two cards makes room by shifting the cards below it (or above, for a drop at the top) inside the same crew lane. Every shifted card is marked "By hand" (decision 5). Overlaps are refused. Late placements are allowed. Crossing crew hours or service hours gives a red warning and is allowed.
- Done when: with cards 1 2 3 4 5, dragging 2 between 4 and 5 gives 1 3 4 2 5 with 3 and 4 moved up; dropping at top and bottom works; in each case the server applies all changes in one transaction.

**P0-6 Editable timeline.** Gantt blocks can be dragged along the time axis (snap 5 minutes, decision 10) and across crew lanes, with the same card operations as the Cards view (lock, select, move, by-hand).
- Done when: the Timeline in standard, compact and detailed views accepts the same drags as the Cards view and syncs the same way.

**P0-7 Crew lane to Unscheduled and back.** Cards move both ways, at any position, with no confirmation.
- Done when: drag from a crew lane to Unscheduled and from Unscheduled into any crew lane position works, and the Unscheduled list accepts a drop at any position.

**P0-8 Multi-select.** A checkbox sits in the top-right corner of each card. The lock icon moves below the checkbox when space is needed. Selected cards drag together and keep their relative times. The group is applied atomically. If any card in the group cannot be placed (overlap), the whole group is refused.
- Done when: selecting three cards and dragging them moves all three; a refused group leaves the board unchanged.

**P0-9 Editable Focus and own-tab views, instant sync.** Focus and own-tab views get the same edits as the main board. Changes made in one view appear in all open views without reload.
- Done when: a move in one tab appears in a second tab of the same browser within about a second (BroadcastChannel plus query invalidation). Cross-device sync is out of scope (decision 9).

### P1

**P1-2 Job-card PDFs.** Two options on the Schedule page: (a) one PDF for all crew, not split; (b) one PDF per crew. The layout follows the board as closely as the PDF allows, with the detailed view density. Include logo, date and all necessary card fields.
- Done when: both downloads work; the page count per crew is correct; the PDF shows the logo and the run date.

**P1-3 Completion status for scheduled jobs.** The Operations "Scheduled work" queue lists scheduled jobs. The admin can set a completion status per job or for many selected jobs. If the status is not "completed", a reason is required. This works after scheduling and after the board is frozen. Service history follows the job status.
- Statuses: the same set the Crew app uses (decision 3).
- Done when: a single job and a bulk selection can each be set; the reason is required for not-completed; the change writes an audit row; the customer service history reflects the status.

**P1-4 Filters hide non-matching cards.** When a top filter (INT, EXT, others) is selected, only matching cards show. A "Show all" switch, off by default, shows the rest in disabled form. The rule applies to every filter on the board and to the Cards, Timeline and Table views.
- Done when: selecting INT hides EXT and other cards; "Show all" brings them back in disabled form.

### P2

**P2-1 "All jobs" counter doubles after a second run.** Reproduce first. The chip counts every row, including skipped rows. Expected: a second run gives the same count as the number of cards.
- Done when: a failing test reproduces the double count, and the fix makes it pass; the chip equals the card count after two runs.

**P2-2 "By hand" stays after a re-run.** An unlocked card that the admin had placed by hand and that the solver re-places keeps `manual = True`. Expected: after an unlock and a new run, the card loses "By hand". Locked cards keep it.
- Done when: a test covers run 1 (hand move), unlock, run 2: the card has no "By hand" flag; a locked card keeps it.

**P2-3 Details tab.** Merge the Details and Society panels into one tab named "Details" on the crew detail page.
- Done when: the crew detail page has one tab named Details containing both sets of fields.

**P2-4 Temporary crew role with dates.** On the crew page, Role and Pairing: the admin can set a role for a date range. With no dates, the change is effective immediately until changed again. With a start date, it applies from that date. With an end date, it applies until that date, then the crew returns to the previous role. Past runs are not affected (decision 7).
- Done when: a dated change applies on the scheduler days it covers and reverts after its end date; a past run is unchanged.

**P2-5 Home zones column.** The crew list page shows home zones as a column, in the same style as other columns.
- Done when: the column appears on the crew list.

**P2-6 Narrower cards.** Reduce card width in the density styles to save space.
- Done when: the board shows more columns per screen in each density, with text still readable.

**P2-7 Car model only.** The card shows the car model only, not the make.
- Done when: the card's vehicle line shows the model only.

**P2-8 Unscheduled sort order.** Display only. Sort the Unscheduled list by EXT first, then ascending cutoff; then INT by ascending cutoff; then other services by ascending cutoff. The scheduler's own ordering does not change.
- Done when: the Unscheduled list order matches the rule in a test.

**P2-9 Unscheduled cards not picked up on later runs.** A card that was taken off by hand keeps `manual = True` and no crew, and the run skips it. Expected (decision 2): later runs re-plan these cards. Only locked cards stay put.
- Done when: a card taken off by hand is placed by run 2 unless it is locked.

### P3

**P3-1 Lock and unlock icons.** Locked: red fill in the empty part of the lock. Unlocked: green fill in the empty part of the lock. The unlocked shackle is rotated 180 degrees towards the left, so open and closed are easy to tell apart.
- Done when: the icons match the three rules in the card and the queue panel.

**P3-2.1 Capacity starts today.** The capacity view defaults to today plus the next 7 days, not to the next Sunday.
- Done when: the default range starts on today's date.

**P3-2.2 Demand tab.** A new tab, Demand, on the capacity page. Clicking a demand cell for a row lists that day's jobs, sorted EXT by cutoff, then INT by cutoff, then other services by cutoff. The list has search and filters in the style of the rest of the site.
- Done when: the tab opens from a demand cell and lists the right jobs in the right order.

**P3-3 Working-slot exceptions.** The current working slots become the "Root" setup. An admin can add a service-wise exception for a date range that changes times or days. An exception overrides Root for its dates only. An exception beats the weekly-off rule for its dates (decision 8). Capacity and the scheduler read the effective slot for each day through one resolver. Nothing is hard-coded.
- Done when: a Wednesday exception makes Wednesday a working day for its range only; outside the range Root applies; the scheduler and capacity agree.

---

## 5. Dependencies and parallel waves

Rule: at most three builders work at the same time. Each builder works in its own git worktree, branched from the integration branch as it stands when the wave starts.

| Wave | Builders (run in parallel) | Items | Why this order |
|---|---|---|---|
| 0 | Prep (one agent, or the lead) | Merge PR #200 first. Create the integration branch from `main`. Fix CLAUDE.md head line. | Every later wave starts from a clean base |
| 1 | A: scheduler run fixes | P2-1, P2-2, P2-9 | Touches `run_schedule` only |
| 1 | B: completion status | P1-3 (backend and Operations UI) | Independent files |
| 1 | C: crew page and temporary roles | P2-3, P2-4, P2-5; migration `0056` | Independent of the board; owns migration `0056` |
| 2 | D: move backend | P0-5, P0-7, P0-8 (backend); batch endpoint | Needs wave 1A merged, because both edit `service.py` |
| 2 | E: board cosmetics and filters | P1-4, P2-6, P2-7, P2-8, P3-1 | Card and board files only |
| 2 | F: capacity and demand | P3-2.1, P3-2.2 | Capacity files only |
| 3 | G: drag engine and card UI | P0-1, P0-5 (UI), P0-7 (UI), P0-8 (UI) | Needs wave 2E (card files) and 2D (move API) |
| 3 | H: PDFs | P1-2 | Needs P2-7 (card fields) from wave 2E |
| 3 | I: working-slot exceptions | P3-3; migration `0057` | Needs `0056` in the chain; touches capacity and scheduler |
| 4 | J: timeline and sync | P0-6, P0-9 | Needs the drag engine from wave 3G |

Migration chain: head `0055` → `0056` (temporary roles, wave 1C) → `0057` (slot exceptions, wave 3I). Wave 3I must build on the integrated `0056`. Check-local fails if there are two heads.

---

## 6. Workflow rules (owner's instructions, binding)

1. **Parallel builders.** Start up to three builders at once, one per wave row. Each works in its own worktree.
2. **Stale tests.** A builder that changes behaviour must update or delete the tests that the change makes stale, so they do not fail for the wrong reason. Each deleted test is listed in the builder's report with the reason.
3. **No individual full checks.** A builder runs only the tests it wrote or changed, with the narrowest command that covers them (for example one pytest file, one Vitest file). Builders do **not** run `tools/dev/check-local.sh`.
4. **Integrated branch.** When every wave's work is done, merge all builder branches into one integration branch. Resolve conflicts there. Keep the owner's files out of the branch: `apps/mobile/ios/*`, `apps/mobile/analysis_options.yaml`, `backlog.md`, `docs/scheduler-workflow*` are not ours.
5. **One local run.** Run `tools/dev/check-local.sh` (the full run, with the PostgreSQL stage) once on the integrated branch. It must pass before push.
6. **CI.** Push the integrated branch and open a regular (ready, not draft) pull request, since the change includes code. Wait for `api-ci`, `web-ci`, `mobile-ci`, `web-e2e` and `ci-gate` to pass. Check once or wait on a single background command; do not write merge scripts or CI watchers.
7. **Merge and deploy.** Merge in the main session when CI is green. A merge to `main` deploys to **test** (the `api-deploy` workflow). Prod is not part of this plan.
8. **Commit hygiene.** Commit only files of this build. Never commit `.env` files or secrets. Commit messages and PR text must not contain vehicle registration numbers. Use the attribution line the session specifies.
9. **Requirements docs.** Every changed requirement row goes back to `Draft` in `docs/feature-status.json` (CLAUDE.md, `/fstatus` rule). Bump the version line of each changed requirements file. Keep the decision file current.
10. **Stop and ask** only if a builder meets a question that is not answered in this plan or in the owner decisions file. Mark the question in the report; do not guess.

---

## 7. Per-wave brief (what each builder receives)

Each builder gets: this file, its wave row, the owner decisions (section 3), its backlog items (section 4), and the rules (section 6). Each builder reports:

- Files changed, with a one-line reason each.
- Tests added, changed, and deleted (with reason).
- Targeted tests run, and their result.
- Any question it could not answer from this plan, with what it did instead.
- The requirement IDs it touched.

### Wave 1A: scheduler run fixes

- Start: `services/api/app/scheduling/service.py`, function `run_schedule`. The placed branch keeps `manual = True` for an unlocked hand placement (P2-2). The unplaced branch skips manual jobs with no crew (P2-9). The counter doubles because the chip counts skipped rows (P2-1).
- Write a failing test first for each of the three bugs, then fix.
- Do not change the scheduler's ordering rules (9-Nov decisions 2 and 7). Frozen days stay as they are.

### Wave 1B: completion status

- Read the crew-side status logic before writing anything. Reuse those exact status values (decision 3).
- Backend: an endpoint to set status for one job or a list of jobs, requiring a reason when not completed; audit row; service history reads the status.
- Frontend: `apps/web/src/pages/operations/OperationsPage.tsx` "Scheduled work" queue: single and bulk actions. Actionable rows are those after scheduling and freeze.

### Wave 1C: crew page and temporary roles

- P2-3: merge Details and Society panels under one "Details" tab (`apps/web/src/pages/crew/CrewDetailPage.tsx`, `crew/panels.tsx`).
- P2-5: home zones column in the crew list (`apps/web/src/pages/crew/CrewListPage.tsx`).
- P2-4: new table for dated role periods, migration `0056`. The scheduler's `load_crew` reads the role for each run day. Past runs are not changed (decision 7). Pairing rules unchanged (decision 11).

### Wave 2D: move backend

- Batch move endpoint: takes a list of job IDs and target positions; applies all in one transaction; refuses the whole batch on any overlap; allows late placements; returns warnings for crew-hours or service-hours crossings.
- Insertion: a single drop shifts the cards in the lane (P0-5). Every shifted card gets "By hand" (decision 5).
- Take-off from a crew lane to Unscheduled sets crew to none; the card is re-planned by later runs unless locked (P2-9 behaviour).
- Start from `move_job` in `service.py` (around the overlap check, line ~820 at planning time) and the take-off branch (~771).

### Wave 2E: board cosmetics and filters

- P1-4 filters: `apps/web/src/pages/schedule/Board.tsx`, `BoardFilters.tsx`, `CardBoard.tsx`, `Timeline.tsx`, `SchedulePage.tsx` filter state. "Show all" off by default.
- P2-6 narrower cards, P2-7 model only, P2-8 Unscheduled sort, P3-1 lock and unlock icons (`schedule.css`, `CardBoard.tsx`, `QueuePanel.tsx`). Note: the unlock icon needs a custom SVG if the library icon is outline-only.

### Wave 2F: capacity and demand

- P3-2.1: `apps/web/src/pages/capacity/CapacityPage.tsx` line ~31 uses `nextSunday()`; change the default to today.
- P3-2.2: Demand tab. A read endpoint lists jobs for one date and service, sorted per the rule. Search and filters in the site's existing style.

### Wave 3G: drag engine and card UI

- Replace native drag with the engine (P0-1). One engine for every view. No confirmation on drop (decision 4).
- Multi-select UI (P0-8): top-right checkbox; lock icon moves below if needed; the group drags together.
- Insertion UI (P0-5): live shift of neighbours during the drag; red warnings for crew or service hours; overlap refusal shown.
- Crew-to-Unscheduled both ways (P0-7).
- Keep the optimistic move with rollback.

### Wave 3H: PDFs

- New module modelled on `services/api/app/billing/pdf.py` (reportlab, the Manrope font). Route under `services/api/app/scheduling/routes`. Two options on the Schedule page (P1-2). Logo from `docs/brand`.

### Wave 3I: working-slot exceptions

- Migration `0057` on top of `0056`. Root = existing `WorkingSlot` rows.
- A resolver returns the effective slot for a service and day: an exception for that day wins; otherwise Root; the weekly-off rule from site working hours is the default when neither applies. Exceptions beat weekly-off on their own dates (decision 8).
- Capacity and the scheduler both call the resolver. Frozen schedules are not changed (ADM-SVS-08).
- UI: `apps/web/src/pages/reference/SlotsTab.tsx`: Root view plus a list of service-wise exceptions with date ranges.

### Wave 4J: timeline and sync

- P0-6: Timeline blocks drag with the engine from wave 3G, snap 5 minutes (decision 10).
- P0-9: BroadcastChannel between tabs in the same browser, plus query invalidation. Cross-device sync is out of scope (decision 9).

---

## 8. Open points

None. The points raised in the first draft are now confirmed decisions 5, 9, 10 and 11 in section 3. No requirement row needs the status **Derived** for them.

## 9. Test coverage expectations

- API: pytest for each new endpoint (batch move, status update, demand list, role periods, slot resolver); pytest for each bug fix (P2-1, P2-2, P2-9) as a regression run across two or three scheduler runs.
- Web: Vitest for drop maths and insertion shifts (Wave 3G), the counter (2-1), the filter rule (P1-4), the sort rule (P2-8), the demand list (P3-2.2).
- E2E (CI only, Playwright): drag across lanes, multi-select, Focus and second-tab sync, completion bulk update.
- Builders run only their own targeted tests (rule 3). The full suite runs once, in the integrated run (rule 5).

---

## 10. Risks

- **Scheduler and solver changes** can move cards that were not expected to move. Keep frozen days and locks as hard constraints in every test.
- **Migrations** must form one chain. Waves 1C and 3I both add migrations; order is fixed by section 5.
- **Native-to-library drag** changes touch and keyboard behaviour. Test on touch if the admin uses a tablet.
- **Stale tests** are the most likely source of false failures. Rule 2 applies.
- **Requirement IDs** must not be renumbered (CLAUDE.md). New rows go at the end of their group.
- **Prod** is not updated by this build. Verify on test before any prod release.
