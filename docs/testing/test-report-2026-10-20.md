# Test report — 20 October 2026

Run on a Windows development PC against `1aa20fc` (branch `update-onboarding-usage-stats`). Unit numbers are in [unit-test-coverage.md](../coverage/unit-test-coverage.md). No device, emulator, hosted database or live provider was used.

## Summary

The first run on 20 Oct found 7 backend failures, 14 scenario failures and two mobile areas under the 90% gate. All were fixed the same day (see "Fixed on 20 Oct" in [unit-test-coverage.md](../coverage/unit-test-coverage.md)); this is the result after the fixes.

| Suite | Result |
|---|---|
| Backend (pytest, SQLite) | 600 passed |
| Mobile unit and widget (`flutter test`) | 1,517 passed, 20 skipped, 0 failed |
| Admin Web unit (Vitest) | 209 passed |
| Scenario widget tests (100, fixture API) | 100 passed |
| Admin Web browser tests (Playwright) | 27 passed |
| Flutter analyze, web lint, web build | clean |
| Security tests | **None exist** |
| Line-coverage gate (90% per area) | Passes in every area (lowest: Crew Mobile 90.33%, Customer Mobile 90.29%) |

## Functional tests

**Scenario widget tests** (`tools/test-data/run-widget-scenarios.ps1`, one pristine fixture database per file). After the fixes all 10 files pass, 100 of 100 tests. The first full run of the day took 22 minutes and 5 of 9 files passed; the final state was confirmed file by file (each file run on its own after the last change), not in one single run, because the machine ran low on memory twice during full runs.

The 14 earlier failures were stale test steps, not app bugs: buttons and the "Latest payment" card now sit below the fold in a lazily built list; "I've paid" and "Pause service" needed scrolling; the Account screen now opens "My vehicles" instead of listing vehicles; one Deep Spa check assumed the chosen day starts with 1; and the complaint-status test ended before its last request finished, which blocked the one-request-at-a-time fixture API and made the next tests fail to sign in.

A second, intermittent version of that stall showed in `scenario_customer_actions_test` (3 tests failing to sign in after the complaint-reply test, in 2 of 3 solo runs). The reply endpoint itself answers in 0.03 s, so the cause is the test setup. Two changes: `letTimersFinish` now lets the screen start its request before waiting, and the complaint-reply test moved to its own file, `scenario_customer_complaint_test.dart`. After that, the actions file passed twice and the complaint file once. Treat the cause as not fully understood; if the stall comes back, look at requests still open when a test ends.

**Requirement IDs in the tests.** 96 tests (69 scenario, 27 Playwright) now carry the IDs they cover in their title, for example `C09 shows the plan, the cycle and a payment that is due [SUB-01, SUB-09, SUB-10]`. The IDs were chosen from each test's name and intent, not by reading every assertion, so they need an owner review. Weakest mappings: NOTIF-01 (notification inbox), AUTH-12 (password form errors) and HOME-02 (every "opens Home" test).

**Admin Web browser tests** (Playwright against the isolated fixture API): 27 passed in 2 min across add-ons, audit, auth, complaints, crew, customers, payments, schedule and settings.

**Not run:** emulator integration tests (`mobile-integration`, GitHub Actions only), real-device tests, Linux golden comparisons, live Resend delivery, hosted PostgreSQL tests. Open list from the scenario work: onboarding walk-through and add vehicle, Deep Spa cancel/change and standalone C08, Admin operations skip, manager skip/reassign, Admin Web creation wizard, capacity and operations, proof media, IST cutoff boundaries.

The latest hosted CI (18 Oct, `f87ecb9`) had `mobile-ci`, `web-ci` and `web-e2e` green and `api-ci` red; the notes attribute `api-ci` to the 89 deferred ruff errors. It did not show the 7 backend failures above, so they may be date-dependent (run on a later day) or specific to this PC. Not checked.

## Security tests

No security test exists and the Security Test stage is empty. What was done:

- 18 Oct 2026 code review (code read, `npm audit`, git history scan). Two findings fixed in `039a5f3`: timed sign-in blocks (15 min, 1 h, 24 h) and safe startup checks. Twelve findings are open: see [security-backlog.md](../security-backlog.md).
- Existing tests that touch security: five-wrong-passwords lock, only the hash stored, wrong-password envelope, and the portal cookie, CSRF and session tests in `tests/webauth`. These ran as part of the backend suite.

Still to write: the every-route-wrong-role test (267 routes), rate-limit tests, the crew privacy test (no customer name or mobile), mobile token storage checks, and the AWS network review.

## Feature status changes

`docs/feature-status.json` was last synced on 13 Oct. On 20 Oct it was reconciled against the three requirements files:

- 461 requirement IDs now (was 419): 42 new, 40 changed since 13 Oct. New and changed rows go back to **Draft**, as the project rule says, including the two that had been at Unit Tested (AUTH-05, CRW-ACC-07). They stay Draft until re-tested against their new wording, even where a passing test cites them.
- Other IDs moved to **Unit Tested** where a passing test file cites them by ID, or the 13 Oct audit lists a targeted regression for them and that test file passes.
- **Functional Tested: 88**: unchanged IDs cited in the title of a passing scenario or Playwright test. 112 IDs are cited in total; the rest are new or changed rows, which stay Draft.
- **Security Test: 0.**
- 15 IDs already at Unit Tested have no test that cites them now (AUTH-06, AUTH-09, AUTH-11, ONB-01, ONB-13 to ONB-17, ONB-20, ADM-ACC-02, ADM-ACC-05, CRW-ACC-01, CRW-ACC-02, CRW-ACC-09). They were left as they were; review them.
- The stage is named "Unit Tested >95%", but no area is measured above 93.3% and three are within 0.4 points of 90%. The stage is promoted on mapped passing tests, as agreed, not on a per-requirement 95% figure.

Result: Draft 88, Backlog 96, In Dev 84, Unit Tested 105, Functional 88, Security 0. Unit Tested fell from 137 because 86 IDs moved up to Functional Tested.

## Still to do

1. Write the security tests listed above; the Security Test stage is empty.
2. Have the owner review the requirement IDs in the test titles (see above).
3. Raise the three areas that pass with under 0.4 points of margin (Customer Mobile, Crew Mobile, Mobile shared); the next feature will push them back under 90% unless it brings its own tests.
4. Re-run all nine scenario files in one go, and the emulator and device tests (GitHub Actions only).
5. The 89 deferred `ruff` errors still fail the `api-ci` check.
