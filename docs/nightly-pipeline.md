# Nightly pipeline (backlog B-70)

**Status:** 04-Nov-26. Design and runbook only. Step 1 of the B-70 plan. No script exists yet. Nothing in this file is switched on.

**Source:** the planning review of 04-Nov-26 (backlog item B-70). Owner decisions are not yet recorded for any open question in section 9. Where a section depends on one, it works with either answer.

## 1. Purpose

Each night, at a set time, take the day's ready pull requests and move them through local checks, merge, test deploy, smoke test and the production release. A failure at any stage stops the run. In the morning the owner reads one report.

The owner's Mac runs the local stages. GitHub Actions stays the final gate for CI, merge, test deploy and smoke test. The existing deploy rules in `docs/build-and-release.md` do not change: merging to `main` deploys to test, and a `v*` tag or a manual run deploys to production after a reviewer approves.

## 2. Stages

Every stage is a hard gate. If a stage fails, the run stops, later stages do not start, and the report says which stage failed and why. The only exception is stage 4, which may drop a pull request and carry on without it.

| # | Stage | What happens | Stops the run when |
|---|---|---|---|
| 0 | Preflight | Take the lock. Check the kill switch. Check tools (git, gh, python, flutter, node, PostgreSQL). Check `main` is green. Check no deploy ran in the last 2 hours (see question 13). | Any check fails. |
| 1 | Select PRs | List eligible pull requests (section 3). Order them. Detect migration clashes and multiple Alembic heads. Comment on and drop any that clash. | No eligible PR (this is a normal quiet night, not an error). |
| 2 | Build the combined branch | Create `nightly/DATE` from `main` and merge the selected PRs in order. Record each PR head commit. | A merge conflict that cannot be resolved by dropping that PR. |
| 3 | Local checks | Run `tools/dev/check-local.sh` with the PostgreSQL stage and the browser tests. | A check fails and stage 4 cannot fix it. |
| 4 | Fix and rerun | Apply the fix loop (section 4). | The limits are used up and the combined branch is still red. |
| 5 | Push and CI | Push the branch. Wait for the required checks (`api-ci`, `web-ci`, `mobile-ci`, `web-e2e`, through the aggregator in section 6). | CI is red or times out. |
| 6 | Merge to `main` | Merge. The method depends on question 6: a merge commit of the combined branch, or each PR in turn. | The merge is refused. |
| 7 | Test deploy and smoke test | Wait for the test deploy. Run the smoke test against test. If red, revert the merge on `main`. | Deploy or smoke test fails. |
| 8 | Production approval gate | Create the release (tag timing is question 9). Wait for the reviewer approval, with a deadline. The owner approves from the phone. | No approval before the deadline, or the owner rejects. |
| 9 | Production deploy | Deploy. Run the production smoke test. On failure, roll back to the previous Vercel deployment. | The smoke test fails (after the rollback). |
| 10 | Morning report | Write the report (section 8.4) and send the notification (question 11). | Never stops the run. It always runs, including after a failure. |

A night with only mobile-app changes follows the same stages up to stage 7. It does not deploy the API to production, and the app-store release stays manual (question 10).

## 3. Which pull requests are eligible

A pull request is eligible when all of these hold:

- It is open and not a draft.
- Its base is `main`.
- It has the label `nightly`, if the opt-in rule is chosen (question 1). If the owner chooses opt-out instead, this condition is dropped and every other condition stays.
- It has none of the labels `no-nightly`, `hold` or `needs-human`.
- GitHub reports it as mergeable.

A pull request that conflicts with another selected one, or adds a migration that clashes with another's, is dropped from that night and gets a comment saying why. Dropping never closes or edits the pull request.

### Labels

| Label | Who sets it | Meaning |
|---|---|---|
| `nightly` | The owner or the PR author | Take this pull request in tonight's run. |
| `no-nightly` | The owner | Never take this pull request. It stays out until the label is removed. |
| `hold` | The owner | Skip for now. Used for a pull request waiting on a decision or another pull request. |
| `needs-human` | The pipeline | The pipeline dropped this pull request and a person must look. The pipeline adds it together with a comment. A person removes it after fixing the cause. |

The labels must be created in the repository before the first run (settings checklist, section 6).

## 4. Fix loop limits

- At most 2 fix attempts per night.
- Mechanical fixes only: lint autofixes and regenerated files (theme, localization, API client, OpenAPI contract). These are the outputs CLAUDE.md says CI fails on when stale.
- A failure that persists after the attempts is traced by running each pull request alone on a clean branch. The pull request that fails alone is dropped, labelled `needs-human` and commented on. The night continues without it.
- Code fixes by Claude are off by default (question 4). If the owner turns them on: they go only to the pull request branch, never to `main` or the combined branch, and they never edit tests. The model and budget are question 5.
- A pull request that fails alone and also fails on `main` points to a broken `main`. The run stops at stage 0 on the next night instead of dropping pull requests one by one.

## 5. Safety features

| Feature | Behaviour |
|---|---|
| Lock | A lock file in the nightly clone. A second run exits at once. A lock older than 6 hours is reported as stale and is not removed automatically. |
| Kill switch | Any one of these stops the run at stage 0 and between stages: a file `KILL` in the nightly clone, `NIGHTLY_ENABLED` not equal to `true`, or the `launchd` job unloaded with `launchctl`. |
| Dry-run | `--dry-run` runs stages 0 to 3 and prints what stages 5 to 9 would do. It pushes nothing, merges nothing and deploys nothing. The first week of real use is dry-run only. |
| Head commit record | The run records the head commit of every selected pull request. If a head moves during the night, that pull request is dropped, so what was tested is what merges. |
| Rollback | A failed test smoke test reverts the merge on `main`. A failed production smoke test rolls production back to the previous Vercel deployment. Production has no automatic rollback today, so this is new work (step 10). |
| Watchdog | A second, separate `launchd` job runs in the morning. If no report exists for the night, it sends the notification "no nightly run". |
| Migration safety | Exactly one Alembic head. Each new migration must be safe to run while the previous API version is still serving (forward-safe). Step 5 builds these checks. |
| Production limits | No unattended production migration before question 14 is confirmed. `NIGHTLY_AUTO_PROD` (step 12) is a later opt-in, for releases with no migrations only. It may never be built. |

### The run-in-its-own-clone rule

The nightly runs in its own clone, for example `~/priveo-nightly`, never in the owner's working checkout. It does `git fetch` and a hard reset to `origin/main` there at the start of every run. It never touches the owner's uncommitted files, branches or worktrees. Secrets and database URLs come from environment configuration for that clone, never committed, and the clone never uses an application database as `TEST_DATABASE_URL`.

## 6. Settings checklist

None of this has been done. Each item needs the owner. Tick them off in the pull request that does the work.

### Repository

- [ ] Create the labels `nightly`, `no-nightly`, `hold`, `needs-human`.
- [ ] Turn on branch protection for `main` (question 7). Today `main` has no protection. The repository is public, so this is available.
- [ ] Add one always-running aggregator job and make it the only required check (question 8). Reason: `api-ci`, `web-ci`, `mobile-ci` and `web-e2e` use path filters, so a pull request that touches only one area never starts the others, and a required check that never starts blocks the merge. The aggregator runs every time, reads the results of the checks that did run, and passes when none failed. Step 7 builds it.
- [ ] Decide whether the owner can still push to `main` in an emergency (hotfix path, question 13).
- [ ] Allow the nightly's token to merge. Use a token with the least rights needed for pull requests, contents and labels. Keep it in the Mac keychain, never in the repository.

### GitHub Environments

- [ ] `test`: no reviewer. Confirm the variables and secrets from `docs/build-and-release.md` are present.
- [ ] `production`: keep the required reviewer. The nightly never removes or bypasses it.
- [ ] Confirm the release workflow can be started by a tag or by a manual dispatch from the nightly's token (question 9).

### Supabase and Vercel

- [ ] Confirm point-in-time recovery or a backup is on for the production database (question 14). Do this before any unattended migration.
- [ ] Confirm the previous production deployment stays available in Vercel, so a rollback can promote it.

### The Mac

- [ ] Create `~/priveo-nightly` as a separate clone.
- [ ] Install the tools stage 0 checks for, including a local PostgreSQL install.
- [ ] Add a `launchd` job for about 02:00 IST (question 2).
- [ ] Add a wake schedule for 01:55 (`pmset repeat wakeorpoweron`). The Mac must be on power and not shut down.
- [ ] Add the morning watchdog job.
- [ ] Set `NIGHTLY_ENABLED=false` at first. Switch it to `true` only after the dry-run week.

### Stale note to confirm

CLAUDE.md says GitHub Actions was stopped by an account billing limit from #75 on. The planning review found recent runs passing, so the note looks stale. This is unconfirmed. Nobody has checked the billing state, and CLAUDE.md is not changed here. The owner should confirm, and then CLAUDE.md can be corrected in a separate change. The design does not depend on the answer for stages 0 to 4, but stages 5 to 7 need working CI.

## 7. Pull request plan

Each step is one small pull request. Sizes are from the planning review. The review's own estimate for the whole item is about 12 to 18 working days, which is larger than the size M the owner set, so expect the item to be split.

| Step | Pull request | Size |
|---|---|---|
| 1 | Design doc, runbook, labels and settings checklist (this file) | S |
| 2 | PR selection and ordering, migration clash and multi-head detection | M |
| 3 | Combined-branch builder, conflict handling | M |
| 4 | Orchestrator: lock, kill switch, preflight, logs, report, launchd, dry-run | M |
| 5 | Migration safety checks (one head, forward-safe on the previous schema) | M |
| 6 | Fix loop and bisect-and-drop | M |
| 7 | CI gate and merge stage, aggregator required-checks job | M |
| 8 | Test-stage wait, extended smoke, revert on red | S |
| 9 | Release stage: tag or dispatch, approval wait and deadline | M |
| 10 | Rollback on a failed production smoke test (tested on test) | M |
| 11 | Notifications and missed-night watchdog | S |
| 12 | Optional `NIGHTLY_AUTO_PROD` | S |

Suggested order: 1, 2, 3, 4 (then dry-run for a week), 5, 6, 7 and 8 (test only), 10, 11, then 9. Step 12 last, or never.

Until step 9 and step 10 are merged and tested on test, the pipeline stops after stage 7 and production stays manual.

## 8. Runbook

The scripts do not exist yet. The commands below are the intended interface. Each step that adds a script must update this section to match what was built.

### 8.1 Start

- Normal: `launchd` starts the run at about 02:00 IST. Nothing to do.
- By hand, dry-run: in `~/priveo-nightly`, run the orchestrator with `--dry-run`. Do this first, and for the first week.
- By hand, real: set `NIGHTLY_ENABLED=true` and run it without `--dry-run`. Not before the dry-run week and the owner's go-ahead.

### 8.2 Stop and disable

- Stop tonight only: create the `KILL` file in `~/priveo-nightly`. The run stops at the next stage boundary. Remove the file to allow the next night.
- Stop a run in progress at once: unload the job with `launchctl` and kill the process. The lock file stays. Check what stage it reached (the log), then remove the lock by hand.
- Disable: set `NIGHTLY_ENABLED=false`, or unload the `launchd` job. Unload the watchdog job too, or it will report a missed night.
- Skip one pull request: add `hold` or `no-nightly` to it.

### 8.3 Approve or reject production

The production release waits for the reviewer in the GitHub Environment `production`. Approve or reject from the GitHub mobile app. If nobody acts before the deadline, the run ends at stage 8 and the release is not deployed. The merge to `main` and the test deploy stay in place. Start the release by hand later with the existing tag or dispatch.

### 8.4 Read the morning report

The report lists, in this order:

1. Result: all stages passed, stopped at stage N, or quiet night.
2. The pull requests taken, with each head commit.
3. The pull requests dropped, each with the reason and a link to the comment.
4. Fix attempts used (of 2) and what changed.
5. Check timings per stage.
6. Test deploy and smoke result.
7. Production state: waiting for approval, deployed, rolled back, or not started.
8. Links to the log file and the GitHub runs.

The log file sits in the nightly clone. The report also goes to the channel chosen in question 11.

### 8.5 Recover from a failed night

First read the report and find the stage that stopped the run. Then:

| Stopped at | State on `main` and test | What to do |
|---|---|---|
| 0 Preflight | Unchanged | Fix the cause the report names (tool, red `main`, stale lock). Run again. |
| 1 to 3 | Unchanged | Look at dropped pull requests, fix, remove `needs-human`, let the next night take them. |
| 4 | Unchanged | Read the failing check. Fix by hand on the pull request. The next night retries. |
| 5 CI | Unchanged | Same as stage 4. The `nightly/DATE` branch can be deleted. |
| 6 Merge | Maybe partly merged | Check `main` against the head-commit record in the report. If merged one by one, revert what the report lists. |
| 7 Test | `main` changed, test red | The pipeline reverts the merge. Confirm the revert landed and test is green again. If not, revert by hand and redeploy test. |
| 8 Approval | Test updated, production old | Nothing is broken. Approve later by hand, or leave it for tomorrow's release. |
| 9 Production | Check production first | Confirm the rollback happened. If not, promote the previous Vercel deployment by hand. Then check the database: a migration may already have run (see below). |

If a migration ran and the release was rolled back, the old API now runs on the new schema. This is why migrations must be forward-safe (step 5) and why question 14 must be confirmed first. If the old API cannot run on the new schema, restore from backup or point-in-time recovery, and do not roll the schema back by guesswork.

A hotfix during the day still uses the manual tag and dispatch. The nightly skips its run if a deploy happened in the last 2 hours (question 13).

## 9. Open questions for the owner

None of these has an answer from the owner. The recommended answers are the planning review's suggestions, not decisions. The backlog lists 14 questions, although the task that asked for this file counted 13.

| # | Question | Status | Works with either answer? |
|---|---|---|---|
| 1 | Opt-in `nightly` label? | Open, recommended answer: yes | Yes. If no, drop the `nightly` condition in section 3. |
| 2 | Run at 02:00 IST on the Mac, and is the Mac always on then? | Open, recommended answer: yes, with a wake schedule | Time is a `launchd` setting. If the Mac is not always on, the watchdog reports the missed night. |
| 3 | Does production keep the approval for the first 10 releases? | Open, recommended answer: yes | Yes. The approval stays until step 12 exists, and step 12 may never be built. |
| 4 | May Claude fix code overnight? | Open, recommended answer: mechanical fixes only at first | Yes. Section 4 describes both. |
| 5 | Model and budget for the fixer, if on? | Open, recommended answer: local or OpenRouter Gemma first, 2 attempts a night | Only matters if question 4 is yes. |
| 6 | One combined PR per night as a merge commit, or one by one? | Open, recommended answer: combined | Stages 2 and 6 name both. Step 3 and step 7 pick one. |
| 7 | Turn on branch protection for `main` now? | Open, recommended answer: yes | Stage 5 and 6 need the required check to be useful, but the pipeline runs without protection. |
| 8 | Which checks are required, given path filters? | Open, recommended answer: one aggregator job | Without it, the required list must be reduced to checks that always run. |
| 9 | Tag on test success, or only when production is approved? | Open, recommended answer: tag on test success | Step 9 builds one of the two. Stage 8 is the same either way. |
| 10 | Mobile-only PRs: merge but no API deploy, with the app-store release manual? | Open, recommended answer: yes | The current iOS and Android release paths are already manual or separate. |
| 11 | Notification channel? | Open, recommended answer: Mac notification plus a GitHub issue until the Resend domain is verified | Step 11 decides. The report file exists whatever is chosen. |
| 12 | No production deploys Friday to Sunday nights, and festival or billing days? | Open, recommended answer: yes | A calendar check in stage 0. The list of days is data, not code. |
| 13 | Hotfix path: keep the manual tag and dispatch, and skip the night if a deploy ran in the last 2 hours? | Open, recommended answer: yes | The manual path is unchanged either way. |
| 14 | Is Supabase point-in-time recovery or a backup on for production before any unattended migration? | Open, recommended answer: confirm before the first run | No. This is a precondition. Without it, a night with a migration must stop at stage 8 and wait for the owner. |

## 10. Risks to watch

- The Mac is a single point of failure. The watchdog tells the owner; it does not run the night elsewhere.
- Production has no automatic rollback today. Do not run stage 9 unattended until step 10 is merged and has been tested on test.
- A forward-unsafe migration can break a rollback. Step 5 is the guard.
- Untested change to CI: the aggregator job and branch protection change how every pull request is merged, not only nightly ones. Turn them on in a quiet period.
- Per-night spend on a fixer model, if question 4 is yes. Follow the model spend order the owner set: local models first.
