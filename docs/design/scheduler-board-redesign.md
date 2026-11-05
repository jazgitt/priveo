# Scheduler board redesign: feature plan

## Context
After a few days of use the owner says the Cards (scrum) and Timeline (Gantt) views work, but the page wastes space. About 300-350px sits above the board (top bar, page header, a three-row date card, 7 tabs, a toolbar, a hint line). The swimlanes get little room and scroll poorly. The cards feel sloppy and slow to react to a drag. EXT and INT jobs look nearly the same. The owner also wants a full-screen focus mode, a searchable table of jobs with crew name and card details, and a lot more room for the board.

## What exists today (from exploration)
- Page: `apps/web/src/pages/schedule/SchedulePage.tsx`. Cards: `CardBoard.tsx`. Gantt: `Timeline.tsx` (view-only). Date strip: `DateBar.tsx`. Styles: `schedule.css` (`@layer legacy`). Helpers: `Board.tsx`. No-scrollbar scroller with drag auto-scroll arrow: `Scroller.tsx`.
- `.sch-col` height is `max(28rem, 100vh - 21rem)`. The 21rem is a hardcoded guess, and `Shell.tsx` wraps the page in `max-w-[90rem] px-4 py-6`.
- Drag and drop is native HTML5. A move is `POST /v1/admin/scheduling/jobs/{id}/move` through `useAppMutation`. There is no optimistic update: toast, then refetch of five queries, and no per-card pending state.
- Job type is only a small code pill (EXT green, INT blue, SPA purple). Status colours override the card fill, so type is lost on done, failed and active cards.
- `AdminJob` already has everything the table needs (`customer_name`, `crew_name`, `vehicle`, `parking`, `service`, `status`, times, `finish_by`, `late`, `manual`, `reason`). `DataTable` (`blocks/DataTable.tsx`) and the shared view toggle (`blocks/view.tsx`) already exist.
- Constraint: ADM-SCH-33 says the page shows no scroll bars and uses arrows (keep `Scroller`). Timeline stays view-only. Drop rules (5-minute snap, confirm when dropping on Unscheduled) stay.

## Features, in build order (each is one PR, serial, local checks first)

### F1. Board gets the screen (layout)
Biggest win, lowest risk.
- Make the Board tab a fixed-height flex layout: the board fills `100dvh` minus the top bar, and only the lanes scroll. This replaces the guessed `21rem`.
- Let the Schedule page use the full viewport width (drop the `max-w-[90rem]` cap for this route only).
- Merge the title and the date strip into one slim sticky bar (about 44px): title, prev/next, day chips, status badge, Freeze/Reassign actions in a menu. The `PageHeader` description line and the hint sentence go. The hint becomes a "?" tooltip.
- Date strip becomes collapsible: collapsed shows only "‹ Thu 06-Nov-26 › · Draft · [Expand]"; expanded shows the 30-day strip. The choice is remembered per user in localStorage. Keep ADM-SCH-35 behaviour (Draft/Frozen/needs-you marks, today selected first).
- Tabs and board toolbar share one row: Board | Needs scheduling | Skipped | Cutoff | Crew queue | Draft improvements, then on the right the view switch, search, status chips. "Run" stays as a button, not a tab, if the owner agrees (see questions).
- Lanes: tighter column header (name, utilisation bar, hours), column width choice (compact 13rem / comfortable 15rem), and stronger sticky headers while lanes scroll.

### F2. Full-screen focus mode (modal)
- A "Focus" button (and key `F`) opens a near-full-viewport dialog (`inset-0`, no max width) with only: day arrows, view switch, search, filters and the board. Esc closes. Drag, drop, job dialog and confirms all work inside it.
- Build as a new `ui/dialog` variant (`size="full"`) in `ui/dialog.tsx`. Move the board into a reusable `<BoardWorkspace>` so the page and the modal render the same component and state (view, search, filters stay in step).
- The `useConfirm` and `JobDialog` layers must stack above the full-screen dialog (check z-index and focus trap).
- Offer "open as its own browser tab" later if the modal is not enough (not in this scope).

### F3. Cards that look and feel right
- Type colours that survive status: the whole card gets a type tint plus a bold left stripe. EXT is green, INT is blue, SPA is purple. Status moves to a small badge/icon (check for Completed, x for Could not complete, a pulsing dot for In progress) so the two never fight for the fill. Keep Late (red) and By hand (gold) as separate corner flags. Apply the same palette to Timeline blocks and the legend (add a legend chip row in the toolbar that doubles as a type filter).
- Card density toggle: Compact (one line: time, code, reg), Standard (today), Detailed (adds customer name and model). Customer name is not on the card today.
- Drag feedback: ghost card, dim the source, highlight valid slots in green and invalid ones in red while dragging, a snapped-time label at the drop line, edge auto-scroll kept.
- Responsiveness: optimistic move (update the cached `board` query on drop, roll back on error), per-card "saving" spinner instead of waiting on a toast, one refetch of `board` and `capacity` instead of five, and no "Moving the job…" loading toast (only an error toast, plus an "Undo" toast on success).
- Keyboard: arrow keys to nudge a selected card by 5 minutes, and Enter to open details (accessibility win).
- Keep native HTML5 drag unless the optimistic work shows it is the bottleneck; evaluate dnd-kit only if touch/trackpad drag is poor (decision for later, not now).

### F4. Table view of jobs
- Add a third view: `Cards | Timeline | Table`, in `Board.tsx` terms a new `JobTable.tsx` using `DataTable`.
- Columns: Time (start-end), Crew name, Registration, Vehicle model, Customer, Parking, Service (type pill with the F3 colours), Duration, Finish by, Status, flags (Late / By hand), Reason (unscheduled).
- Search box (as always) over registration, customer, crew, parking and model, shared with the other views. Filters: crew, type, status. Sort by any column; default sort is crew then start time. Unscheduled jobs show "Unassigned" and sort to the top.
- Row click opens the same `JobDialog`, so a job can be moved or reassigned from the table too. Count in the footer, CSV export of the day (one button).
- Remember the last view per user (`useViewMode` pattern).

### F5. Search and filters that work everywhere
- One search state shared by the three views and the focus modal. Today `matches` covers registration and parking only; extend it to customer, crew and model (update `Board.test.tsx`).
- In Cards and Timeline, non-matching jobs dim instead of disappearing, and the first match scrolls into view.
- Filter chips: type (EXT/INT/SPA), status, late only, by hand only, and a crew picker to show only chosen lanes.

### F6. Lane scrolling and crew handling (polish)
- Pin the Unscheduled column at the left while crew lanes scroll horizontally.
- Option to collapse a crew lane to a thin strip, and to hide "Off" crew.
- Mouse-wheel/shift-wheel and drag-to-pan on the board background, with the arrow indicators kept.

## Docs and tracking (every PR)
- `docs/reqs/admin-functional-requirements.md`: update ADM-SCH-33 (layout, card colours, table view), add new IDs at the end of the ADM-SCH group (focus mode, table view, collapsible date strip, card density, shared search and filters), bump the version line, and mark new rows **Derived** until the owner confirms. Run the ID cross-reference check afterwards.
- `docs/feature-status.json`: new rows start at Draft; ADM-SCH-32 to 36 changes go back to Draft too.
- `docs/design/admin-portal-ui-review.md` §4: add a short note on the new layout.
- `README.md`: no change unless the prototype differences list changes.

## Tests
- Vitest (`SchedulePage.test.tsx`, `Board.test.tsx`): update for changed class names/labels (`sch-card`, status classes, collapsed date bar); add tests for the optimistic move and rollback, table view columns/search/sort, focus mode open/Esc, type colour classes, and extended `matches`.
- Playwright (`e2e/schedule.spec.ts`): add a drag-a-card e2e, a search e2e, a table view e2e and a focus-mode e2e (currently there is no board coverage).
- Run `tools/dev/check-local.sh --changed` before each PR. This is web-only unless F3 needs an API change, so the PostgreSQL stage is not needed unless the move endpoint changes.

## Order and risk
1. F1 (layout) alone fixes the main complaint. 2. F3 card look and optimistic moves. 3. F4 table and F5 search. 4. F2 focus mode (reuses F1's workspace component). 5. F6 polish.
Main risks: existing tests tied to CSS class names; the no-scrollbar requirement; stacking dialogs over the full-screen modal; optimistic updates must roll back cleanly on `schedule_frozen`.

## Verification
Run the portal locally (`tools/dev/run-local`, see memory "Where things live") with the seeded two societies, then check: the board fills the window at 1366x768 and 1920x1080; collapse/expand the date strip; drag a card and see it move instantly, with rollback on a frozen day; EXT/INT/SPA are distinguishable on Scheduled, Completed and Failed cards; search in all three views; the table shows crew and card details and opens the job dialog; the focus modal opens, works and closes with Esc. Then `npm run lint`, `npm test`, `npm run build` and `npm run e2e` from `apps/web`.

## Owner decisions (5-Nov-26)
1. "Run" becomes a button in the slim header, not a tab.
2. Table view is read-only; a row click opens the job dialog.
3. Besides the focus modal, the board can open alone in a new browser tab ("exclusive" mode).

### F2b. Board in its own browser tab
- New route `/schedule/board?site=&date=` rendered outside `Shell` (no top bar, no nav), same auth guard, only the day arrows, view switch, search, filters and the board.
- Reuses `<BoardWorkspace>` from F2. State (view, search, filters, density) comes from the URL and localStorage so the tab survives a reload.
- "Open in new tab" button next to "Focus" (`window.open`, `noopener`). Both windows refresh from the same queries; the tab refetches on window focus so a move in one shows in the other.
- Built together with F2 (same PR).
