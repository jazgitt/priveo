# Shared brief for scheduler board builders (v1.0, 10-Nov-26)

Read with `docs/plans/scheduler-board-fixes-build-plan.md` (sections 3, 4, 6, 7). Owner decisions: `docs/reqs/owner-decisions-2026-11-09.md` and section 3 of the build plan.

## Rules for every builder
- Work only in your own worktree, branched from `integrate/scheduler-board-fixes`. Run `npm install` in `apps/web` yourself. Never symlink `node_modules`.
- Write the implementation AND its tests (pytest, Vitest, Playwright spec where the plan lists one).
- **Do not run any tests** and do not run `tools/dev/check-local.sh`. The owner's instruction for this build is one integrated run at the end.
- If a change makes an existing test stale, update or delete it. List each deleted test with the reason.
- Commit only your own files. Never commit `.env` or secrets. No vehicle registration numbers in commit messages or PR text.
- New requirement IDs go at the end of their group. Changed requirement rows go back to `Draft` in `docs/feature-status.json`. Bump the version line of each changed requirements file.
- Report at the end: files changed (one-line reason each), tests added/changed/deleted (with reason), requirement IDs touched, open questions and what you did instead.

## Pinned contracts (do not change without telling the lead)

### Batch move (D provides, G1 consumes)
`POST /admin/jobs/batch-move` (admin role, same guard as `/admin/jobs/{job_id}/move`).

Request:
```json
{
  "moves": [
    {"job_id": "uuid", "crew_id": "uuid | null", "start_minute": 0}
  ],
  "override": false
}
```
- `crew_id: null` takes the job off its crew (goes to Unscheduled).
- All moves apply in ONE transaction. Any overlap refuses the whole batch with HTTP 409 and body `{"detail": {"code": "overlap", "job_ids": [...]}}`.
- Late placements (after cutoff) are allowed.
- Crew-hours or service-hours crossings do NOT refuse. They return warnings.

Response 200:
```json
{
  "jobs": [ /* AdminJob, same shape as the single-move response */ ],
  "warnings": [
    {"job_id": "uuid", "code": "crew_hours | service_hours", "message": "string"}
  ]
}
```
Insertion: the lead's client sends the dragged card plus every card the server must shift. The server computes shifts from `start_minute` and the lane order, and marks every shifted card `manual = True` ("By hand").

Web client function name: `batchMoveJobs(moves, override)` in `apps/web/src/pages/schedule/api.ts`. G1 writes it against the contract above. D must match these names.

### Migrations (chain is fixed)
- Head on `integrate/scheduler-board-fixes`: `0055` (`20261109_0055_cutoff_driven_objectives.py`).
- C creates `0056` (temporary crew roles), `down_revision = "0055"`.
- I creates `0057` (working-slot exceptions), `down_revision = "0056"`.
- Only these two migrations. No other builder adds one.

### Completion statuses (B)
Use the exact values the crew app already uses in `set_job_status` (`services/api/app/scheduling/service.py`). Do not invent values. B reports the list it reused.

### Stable names other builders depend on
- Drag engine module lives in `apps/web/src/pages/schedule/dnd/` (G1 owns it). E and J/G2 import from there. E does not implement drag.
- Card fields for the PDF: the card shows car model only (P2-7, E). H reads the model field directly from the job row.

## Ownership (who may edit what)
- A: `services/api/app/scheduling/service.py` (`run_schedule` only), `run_counts.py`, tests for them.
- B: status endpoint and its schemas, `services/api/app/.../service.py` only for a new function appended at the end, `apps/web/src/pages/operations/OperationsPage.tsx`.
- C: crew routes and pages, migration `0056`, `crew_rules.py`, `load_crew` read path.
- D: new batch-move module and route, `move_job` hook-in only through a call, not an edit of `move_job` body.
- E: `Board.tsx`, `BoardFilters.tsx`, `CardBoard.tsx` (visual and filter code only), `Timeline.tsx` (filter only), `schedule.css`, `QueuePanel.tsx` (sort and icons only).
- F: `apps/web/src/pages/capacity/CapacityPage.tsx`, new demand endpoint and module.
- G1: `apps/web/src/pages/schedule/dnd/` (new), `apps/web/src/pages/schedule/api.ts` (add `batchMoveJobs` only), BroadcastChannel sync module.
- G2: `CardBoard.tsx` and `QueuePanel.tsx` drag wiring, multi-select checkbox.
- H: new PDF module and route, buttons in `apps/web/src/pages/schedule/ScheduleActions.tsx`.
- I: slot resolver module, `capacity.py`, the scheduler's slot read, `apps/web/src/pages/reference/SlotsTab.tsx`, migration `0057`.
- J: `Timeline.tsx` drag wiring, sync wiring to query invalidation.

Shared files, edit only the minimum and expect conflicts at integration: `service.py` (A, B, C, D, I), `CardBoard.tsx` (E, G2), `Timeline.tsx` (E, J), `api.ts` (B, G1, F).
