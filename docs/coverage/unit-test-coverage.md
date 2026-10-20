# Automated test coverage — 20 October 2026

Baseline: `1aa20fc` on branch `update-onboarding-usage-stats` (`main` plus the ONBOARDING.md edit), plus uncommitted test fixes and the new tests listed below. The figures come from suites run on 20 Oct 2026. They replace the 13 Oct 2026 measurement. The threshold is **90% executable line coverage for each application area**; shared code is measured separately so an overall average cannot hide a weak role.

**Result: the gate passes in every area**, with a small margin in Customer Mobile (90.29%), Crew Mobile (90.33%) and Mobile shared (90.38%).

| Application area | Covered / executable lines | Line coverage | 90% gate | 13 Oct |
|---|---:|---:|---|---:|
| Customer Mobile | 5,160 / 5,715 | **90.29%** | Pass | 90.22% |
| Crew Mobile | 1,523 / 1,686 | **90.33%** | Pass | 90.09% |
| Admin Mobile | 1,385 / 1,519 | **91.18%** | Pass | 91.17% |
| Admin Web | 2,682 / 2,916 | **91.98%** | Pass | 90.52% |
| Shared backend/API | 9,360 / 10,031 | **93.31%** | Pass | 92.89% |
| Shared mobile/auth/UI | 1,324 / 1,465 | **90.38%** | Pass | 92.85% |
| Generated mobile API/localization | 4,215 / 4,216 | **99.98%** | Pass | 99.98% |
| Entire mobile application, including generated code | 13,607 / 14,601 | **93.19%** | Pass | 93.45% |
| All application sources combined | 25,649 / 27,548 | **93.11%** | Pass | 93.03% |

`tools/coverage/report.py` exits 0. Per-file detail and missing lines are in `unit-test-coverage.json`.

## Execution evidence (20 Oct 2026)

- **Backend (API): 600 passed, 0 failed** (SQLite, line and branch instrumentation, 6 min 30 s). The morning run had 7 failures; see "Fixed on 20 Oct" below.
- **Mobile: 1,517 passed, 20 skipped, 0 failed** (13 Oct: 1,433 passed, 11 skipped). The skips need Linux goldens or a live API and do not count as passing; the 20 probably include the 9 scenario files that need the fixture API, which was not checked.
- **Admin Web: 209 passed** in 26 files (13 Oct: 99). The web run was made earlier on 20 Oct; no web code changed afterwards. Statements 89.87%, branches 78.4%, functions 86.43%.
- `flutter analyze`: no issues. `npm run lint`: clean. `npm run build`: passes.
- Scenario widget tests (fixture API): 100 of 100 pass when each file is run through `tools/test-data/run-widget-scenarios.ps1`. Playwright: 27 of 27. Details in [../testing/test-report-2026-10-20.md](../testing/test-report-2026-10-20.md).
- Not run: API lint (`ruff` still reports the 89 deferred errors), PostgreSQL checks, any device or emulator test, live provider delivery, deployment.

## Other coverage metrics

90% line coverage does not mean 90% branch or function coverage.

| Metric | Backend | Admin Web |
|---|---:|---:|
| Branches | 81.24% | 78.40% |
| Statements | 93.31% (lines) | 89.87% |
| Functions | Not separately measured | 86.43% |

## Fixed on 20 Oct

- **Coverage script:** `tools/coverage/run.ps1` set `TEST_DATABASE_URL=sqlite://` (in-memory), which the four migration tests cannot use. It now leaves the variable unset, so the tests use their own SQLite file.
- **Operations tests:** three tests used a fixed 2026 date that had gone stale (`retry_date_passed`). `tests/scheduling/test_operations.py` now pins today's date to the API tests' clock.
- **Scenario tests:** 14 failed on stale steps (buttons below the fold in lazily built lists, renamed labels, a date check that assumed a day starting with 1, the Account screen no longer listing vehicles, and one test that ended before its last request finished). All fixed in the test files; no app code changed.
- **New tests:** `test/changes_money/subscription_screen_test.dart` (4 tests: plan inclusions, list price and plan ID, open add-ons, paused and inactive plans) and `test/crew/providers_test.dart` (6 tests: upload owner, queue store, upload client, queue start). They lifted Customer Mobile from 89.50% and Crew Mobile from 89.15% to over 90%.
- **Report tool:** `lib/features/splash/splash_strings.dart` holds only constants and has no executable lines, so it can never appear in the coverage data. It is now listed as a declarative source in `tools/coverage/report.py`, next to `tokens.g.dart` and `main.dart`.

## Repeat the measurement

```powershell
.\tools\coverage\run.ps1
```

The script stops at the first failing step. On a PC with little free memory, run the steps one at a time (backend, `flutter test --coverage ... --concurrency=2`, web, then `tools/coverage/report.py`): a full run was stopped once for low memory.
