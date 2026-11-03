# Nightly pipeline (backlog B-70)

**Status:** 04-Nov-26, updated the same evening for the build. Steps 2 to 8, 10 and 11 of the B-70 plan are built for the **test path only**. The scripts live in `tools/nightly/`.

**Source:** the planning review of 04-Nov-26 (backlog item B-70), and the owner's message of 04-Nov-26 that approved the test-path scope.

**Owner decisions of 04-Nov-26 (Owner):**
- Build the test path only. Step 9 (production release) and step 12 (`NIGHTLY_AUTO_PROD`) are **not built**. The pipeline has no code path that deploys to production, touches the production database or creates a tag. Production stays manual (`docs/build-and-release.md`).
- Create the labels `nightly`, `no-nightly`, `hold`, `needs-human`. Turn on branch protection on `main` with one aggregator check, after that check has run green on `main`. Install the `launchd` job on the owner's Mac, running from a dedicated clone `~/priveo-nightly`.
- Every run must leave a log trace of everything tested locally and on test (section 8.6).

**Everything else below that answers an open question is Derived**, from the recommended answers in section 9. It is not an owner decision.

## 1. Purpose

Each night, at a set time, take the day's ready pull requests and move them through local checks, merge, test deploy, smoke test and the production release. A failure at any stage stops the run. In the morning the owner reads one report.

The owner's Mac runs the local stages. GitHub Actions stays the final gate for CI, merge, test deploy and smoke test. The existing deploy rules in `docs/build-and-release.md` do not change: merging to `main` deploys to test, and a `v*` tag or a manual run deploys to production after a reviewer approves.

## 2. Stages

Every stage is a hard gate. If a stage fails, the run stops, later stages do not start, and the report says which stage failed and why. The only exception is stage 4, which may drop a pull request and carry on without it.

| # | Stage | What happens | Stops the run when |
|---|---|---|---|
| 0 | Preflight | Take the lock. Check the kill switch. Check tools (git, gh, python, flutter, node, PostgreSQL). Check `main` is green. Check no deploy ran in the last 2 hours (see question 13): if one did and it will be 2 hours old within 90 minutes, the run waits, otherwise it skips the night. | Any check fails. |
| 1 | Select PRs | List eligible pull requests (section 3). Order them. Detect migration clashes and multiple Alembic heads. Comment on and drop any that clash. | No eligible PR (this is a normal quiet night, not an error). |
| 2 | Build the combined branch | Create `nightly/DATE` from `main` and merge the selected PRs in order. Record each PR head commit. | A merge conflict that cannot be resolved by dropping that PR. |
| 3 | Local checks | Run `tools/dev/check-local.sh` with the PostgreSQL stage and the browser tests. | A check fails and stage 4 cannot fix it. |
| 4 | Fix and rerun | Apply the fix loop (section 4). | The limits are used up and the combined branch is still red. |
| 5 | Push and CI | Push the branch. Wait for the required checks (`api-ci`, `web-ci`, `mobile-ci`, `web-e2e`, through the aggregator in section 6). | CI is red or times out. |
| 6 | Merge to `main` | Open one pull request `nightly/DATE` to `main`, wait for the required check, and merge it with a merge commit (Derived: combined, one merge per night). The included pull requests are marked merged by GitHub because their head commits are now in `main`. | The merge is refused. |
| 7 | Test deploy and smoke test | Find the `api-deploy` run for the merge commit and wait for it. Read the result of its smoke test step. Check `/v1/public/health` on test. If red, revert the merge on `main` (which deploys test again) and check that deploy. | Deploy or smoke test fails. |
| 8 | Production approval gate | **Not built (tonight's scope).** Production stays manual. | Not applicable. |
| 9 | Production deploy | **Not built (tonight's scope).** There is no code path to production. | Not applicable. |
| 10 | Morning report | Write the report (section 8.4), post it on each merged pull request, and send the notification (question 11). | Never stops the run. It always runs, including after a failure. |

The run ends after stage 7 (test deployed and smoke tested) and stage 10. The stage numbers stay as in the plan so that stages 8 and 9 can be added later without renumbering.

A night with only mobile-app changes follows the same stages up to stage 7. There is no `api-deploy` run for it, and the report says so. The app-store release stays manual (question 10).

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

- At most 2 fix attempts per night (Derived).
- Mechanical fixes only: lint autofixes and regenerated files (theme, localization, API client, OpenAPI contract). These are the outputs CLAUDE.md says CI fails on when stale.
- A failure that persists after the attempts is traced by running each pull request alone on a clean branch. The pull request that fails alone is dropped, labelled `needs-human` and commented on. The night continues without it.
- Code fixes by Claude are **not built** (question 4, Derived: mechanical fixes only). If the owner turns them on later, they must go only to the pull request branch, never to `main` or the combined branch, and never edit tests. The model and budget are question 5.
- The mechanical fixes are: `ruff check --fix`, `npm run lint -- --fix`, `dart run tool/gen_theme.dart`, `flutter gen-l10n`, `dart run tool/gen_api.dart`, and `scripts/export_openapi.py`. A fix is committed on the combined branch as `nightly: regenerate files`.
- A pull request that fails alone and also fails on `main` points to a broken `main`. The run stops at stage 0 on the next night instead of dropping pull requests one by one.

## 5. Safety features

| Feature | Behaviour |
|---|---|
| Lock | A lock file in the nightly clone. A second run exits at once. A lock older than 6 hours is reported as stale and is not removed automatically. |
| Kill switch | Any one of these stops the run at stage 0 and between stages: a file `KILL` in the nightly clone, `NIGHTLY_ENABLED` not equal to `true`, or the `launchd` job unloaded with `launchctl`. |
| Dry-run | `--dry-run` runs stages 0 to 3 and prints what stages 5 to 7 would do. It pushes nothing, merges nothing, labels nothing and deploys nothing. The planning review asked for a week of dry-runs first. The owner chose to let the first real run happen on the night of 04-Nov-26. |
| No production path | The scripts never start a production deploy, never push a tag and never read a production variable. `tools/nightly/tests/test_no_production.py` fails if any script mentions the production environment, a tag push or the production project. |
| Head commit record | The run records the head commit of every selected pull request. If a head moves during the night, that pull request is dropped, so what was tested is what merges. |
| Rollback | A failed test deploy or smoke test reverts the merge on `main` (a revert of the merge commit), which deploys test again. The revert is exercised on test by `tools/nightly/rollback.py` (a drill). Production rollback is not built. |
| Watchdog | A second, separate `launchd` job runs at 06:30. If no real run left a report in the last 24 hours, it sends the notification "no nightly run" and opens a GitHub issue. |
| Migration safety | Exactly one Alembic head. Each new migration must be safe to run while the previous API version is still serving (forward-safe). Step 5 builds these checks. |
| Production limits | Production is outside the pipeline. `NIGHTLY_AUTO_PROD` (step 12) is not built and may never be. |

### The run-in-its-own-clone rule

The nightly runs in its own clone, for example `~/priveo-nightly`, never in the owner's working checkout. It does `git fetch` and a hard reset to `origin/main` there at the start of every run. It never touches the owner's uncommitted files, branches or worktrees. Secrets and database URLs come from environment configuration for that clone, never committed, and the clone never uses an application database as `TEST_DATABASE_URL`.

## 6. Settings checklist

Items ticked were done on 04-Nov-26 with the owner's approval. The rest still need the owner.

### Repository

- [x] Create the labels `nightly`, `no-nightly`, `hold`, `needs-human` (Owner approved, done 04-Nov-26).
- [x] Turn on branch protection for `main` (question 7). Owner approved 04-Nov-26; see section 12 for the exact settings. Today `main` has no protection. The repository is public, so this is available.
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

- [x] Create `~/priveo-nightly` as a separate clone (`tools/nightly/setup-clone.sh`).
- [ ] Install the tools stage 0 checks for, including a local PostgreSQL install.
- [x] Add a `launchd` job for about 02:00 IST (`tools/nightly/install-launchd.sh`).
- [ ] Add a wake schedule for 01:55. This needs `sudo`, so the pipeline does not do it: `sudo pmset repeat wakeorpoweron MTWRFSU 01:55:00`. The Mac must be on power and not shut down.
- [x] Add the morning watchdog job (installed by the same script).
- [x] `NIGHTLY_ENABLED` lives in `~/priveo-nightly/nightly.env`. The owner chose to have it `true` for the first night.

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

The scripts are in `tools/nightly/`. Each step that changes a script must update this section.

### 8.1 Start

- Normal: `launchd` starts the run at about 02:00 IST. Nothing to do.
- By hand, dry-run: `~/priveo-nightly/tools/nightly/run-nightly.sh --dry-run`. It builds the combined branch locally and runs the local checks, and changes nothing on GitHub. Add `--skip-checks` to skip the long local checks.
- By hand, real: `~/priveo-nightly/tools/nightly/run-nightly.sh` (needs `NIGHTLY_ENABLED=true` in `~/priveo-nightly/nightly.env`).
- First-time setup: `tools/nightly/setup-clone.sh` (creates the clone, the virtualenv and the installs), then `tools/nightly/install-launchd.sh`.

### 8.2 Stop and disable

- Stop tonight only: create the `KILL` file in `~/priveo-nightly`. The run stops at the next stage boundary. Remove the file to allow the next night.
- Stop a run in progress at once: unload the job with `launchctl` and kill the process. The lock file stays. Check what stage it reached (the log), then remove the lock by hand.
- Disable: set `NIGHTLY_ENABLED=false`, or unload the `launchd` job. Unload the watchdog job too, or it will report a missed night.
- Skip one pull request: add `hold` or `no-nightly` to it.

### 8.3 Production

Not part of the pipeline. After a green night, check test, then release by hand as in `docs/build-and-release.md` (tag and approve). The report says "Production: untouched (manual)".

### 8.4 Read the morning report

The report lists, in this order:

1. Result: all stages passed, stopped at stage N, or quiet night.
2. The pull requests taken, with each head commit.
3. The pull requests dropped, each with the reason and a link to the comment.
4. Fix attempts used (of 2) and what changed.
5. Check timings per stage.
6. Test deploy and smoke result.
7. Production: always "untouched (manual)" in this version.
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

A hotfix during the day still uses the manual tag and dispatch. The nightly waits (up to 90 minutes) or skips its run if a deploy happened in the last 2 hours (question 13).

### 8.6 The log trace

See section 11 for the files. After a night: open `~/priveo-nightly/logs/<date>/report.md` first; `manifest.json` has the machine-readable record; `events.jsonl` lists every command with times and exit codes; `commands/` holds the full output.

## 9. Open questions for the owner

The owner answered only the scope items listed at the top of this file. For the rest, the build used the recommended answer and marks it **Derived**. Questions 3, 9, 12 and 14 do not apply to a pipeline without production. Question 9 (tagging) is not done at all. The backlog lists 14 questions, although the task that asked for this file counted 13.

| # | Question | Status | Works with either answer? |
|---|---|---|---|
| 1 | Opt-in `nightly` label? | Derived, recommended answer used: yes | Yes. If no, drop the `nightly` condition in section 3. |
| 2 | Run at 02:00 IST on the Mac, and is the Mac always on then? | Derived, recommended answer used: yes, with a wake schedule | Time is a `launchd` setting. If the Mac is not always on, the watchdog reports the missed night. |
| 3 | Does production keep the approval for the first 10 releases? | Derived, recommended answer used: yes | Yes. The approval stays until step 12 exists, and step 12 may never be built. |
| 4 | May Claude fix code overnight? | Derived, recommended answer used: mechanical fixes only at first | Yes. Section 4 describes both. |
| 5 | Model and budget for the fixer, if on? | Derived, recommended answer used: local or OpenRouter Gemma first, 2 attempts a night | Only matters if question 4 is yes. |
| 6 | One combined PR per night as a merge commit, or one by one? | Derived, recommended answer used: combined | Stages 2 and 6 name both. Step 3 and step 7 pick one. |
| 7 | Turn on branch protection for `main` now? | Derived, recommended answer used: yes | Stage 5 and 6 need the required check to be useful, but the pipeline runs without protection. |
| 8 | Which checks are required, given path filters? | Derived, recommended answer used: one aggregator job | Without it, the required list must be reduced to checks that always run. |
| 9 | Tag on test success, or only when production is approved? | Derived, recommended answer used: tag on test success | Step 9 builds one of the two. Stage 8 is the same either way. |
| 10 | Mobile-only PRs: merge but no API deploy, with the app-store release manual? | Derived, recommended answer used: yes | The current iOS and Android release paths are already manual or separate. |
| 11 | Notification channel? | Derived, recommended answer used: Mac notification plus a GitHub issue until the Resend domain is verified | Step 11 decides. The report file exists whatever is chosen. |
| 12 | No production deploys Friday to Sunday nights, and festival or billing days? | Derived, recommended answer used: yes | A calendar check in stage 0. The list of days is data, not code. |
| 13 | Hotfix path: keep the manual tag and dispatch, and skip the night if a deploy ran in the last 2 hours? | Derived, recommended answer used: yes | The manual path is unchanged either way. |
| 14 | Is Supabase point-in-time recovery or a backup on for production before any unattended migration? | Derived, recommended answer used: confirm before the first run | No. This is a precondition. Without it, a night with a migration must stop at stage 8 and wait for the owner. |

## 10. Risks to watch

- The Mac is a single point of failure. The watchdog tells the owner; it does not run the night elsewhere.
- Production has no automatic rollback today. Do not run stage 9 unattended until step 10 is merged and has been tested on test.
- A forward-unsafe migration can break a rollback. Step 5 is the guard.
- Untested change to CI: the aggregator job and branch protection change how every pull request is merged, not only nightly ones. Turn them on in a quiet period.
- Per-night spend on a fixer model, if question 4 is yes. Follow the model spend order the owner set: local models first.

## 11. Evidence trace (Owner requirement)

Every run, dry or real, writes a trace to `~/priveo-nightly/logs/<folder>/`. The folder is the date (`YYYY-MM-DD`) for a real run and `YYYY-MM-DD-dryrun-HHMM` for a dry run. A second real run on the same date gets `-2`.

| File | Content |
|---|---|
| `events.jsonl` | One JSON line per event: stage start, stage end (with pass or fail), each command with its start time, end time, exit code and the log file holding its output. |
| `commands/NN-name.log` | The full output of each command. |
| `manifest.json` | Machine-readable record: mode, result, the pull requests taken (number, head commit, title), the pull requests dropped with reasons, the local checks that ran (each stage line from `check-local.sh`, including the PostgreSQL run and the browser tests), the CI run links, the merge commit, the test deploy run link and the smoke test result. |
| `report.md` | The morning report (section 8.4), the same text that is posted on each merged pull request and in the GitHub issue. |

The trace holds no secrets: commands are logged as written, and no script puts a password or a database address on a command line. Home folder paths are shortened to `~` in anything posted to GitHub.

## 12. What was set up

### Branch protection on `main`

Set through the GitHub API, after the `ci-gate` check had run green on `main`:

- Required status check: `ci-gate` only. Not strict (a branch need not be up to date).
- No required reviews.
- `enforce_admins` off, so an admin can still merge by hand, or push in an emergency.
- Force pushes and deletion of `main` off.

`ci-gate` (`.github/workflows/ci-gate.yml`) runs on every pull request, including docs-only and path-filtered ones. It waits for the other checks that started for the same commit, and passes when none failed. A pull request opened before `ci-gate` existed has no such check: an admin merges it with the bypass, or pushes an empty commit to start the check.

To undo: Settings, Branches, delete the rule, or `gh api -X DELETE repos/jazgitt/priveo/branches/main/protection`.

### launchd

- `in.priveo.nightly`: starts `~/priveo-nightly/tools/nightly/run-nightly.sh` at 02:00 local time (IST on this Mac).
- `in.priveo.nightly-watchdog`: starts `watchdog.py` at 06:30.
- Plists are in `~/Library/LaunchAgents/`. Stop with `launchctl bootout gui/$(id -u)/in.priveo.nightly`.
- Wake at 01:55 needs `sudo pmset repeat wakeorpoweron MTWRFSU 01:55:00` (not done by the pipeline). A missed 02:00 start runs when the Mac wakes. The run holds `caffeinate` so the Mac does not sleep during it.

## 13. Built state (04-Nov-26)

- Code: `tools/nightly/` (PRs #118, #120, #121, #122, #123, #124, #125, #126). Tests: `python3 -m unittest discover -s tools/nightly/tests`. They are not in a CI workflow; run them after changing the scripts.
- The clone's virtualenv uses `python3.12` (`NIGHTLY_PYTHON` overrides), because the default `python3` has no ortools wheel.
- Rollback drill on test (PR #127): a harmless file was merged, then `tools/nightly/rollback.py` reverted the merge on `main`. The revert deployed test, the smoke test step passed and `/v1/public/health` showed the run's build number. Net change in the repository: none.
- `ci-gate` is the only required check on `main`. Admins are not bound by it (`enforce_admins` off).
- Not built, by the owner's scope: stages 8 and 9, production rollback, `NIGHTLY_AUTO_PROD`, any tagging, Claude code fixes.
