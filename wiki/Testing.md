# Testing

**Testing** in Priveo combines backend tests, mobile unit/widget tests, portal unit/browser tests, scenario fixtures and per-area executable-line coverage. The most recent reviewed measurement is dated 20 October 2026.[^1][^2]

## Recorded results

| Suite or check | Recorded outcome |
|---|---|
| Backend pytest, SQLite | 600 passed |
| Mobile unit/widget | 1,517 passed; 20 skipped |
| Portal unit tests | 209 passed |
| Scenario widget tests | 100 passed, confirmed file by file |
| Portal Playwright tests | 27 passed |
| Flutter analysis, portal lint/build | Clean/passing |
| Comprehensive security tests | Not established |

These are recorded historical results, not a new run performed while writing this wiki. The report ties them to baseline `1aa20fc` plus the described local fixes. Scenario confirmation was file by file after fixes because full runs encountered memory pressure; it was not one final uninterrupted combined run.[^1]

## Coverage

The gate is 90% executable-line coverage for each application area, with shared and generated code reported separately. It is not a branch-coverage target or per-requirement proof.[^2]

| Area | Recorded line coverage |
|---|---:|
| Customer Mobile | 90.29% |
| Crew Mobile | 90.33% |
| Admin Mobile | 91.18% |
| Admin Web | 91.98% |
| Shared backend/API | 93.31% |
| Shared mobile/auth/UI | 90.38% |

Generated code has its own high coverage and must not hide weak application areas in a combined average. The report records backend branch coverage of 81.24% and portal branch coverage of 78.40%.[^2]

## Fixtures and scenarios

The synthetic catalogue contains 40 families covering subscriptions, standalone services, payments, skips, pauses, complaints, workforce and administrative scenarios. A family has isolated dependencies so local reset can target selected cases. Scenario state deliberately separates vehicle activity, subscription state, add-on state and payment state.[^3]

Local SQLite fixtures support guarded fresh-start/reset workflows. The hosted-dev seeder is different: it adds synthetic PostgreSQL data without resetting existing records, preserves edits on repeat runs and has an explicit synthetic-account password synchronization mode. Neither should be confused with the real-customer importer.[^3]

## Requirement mapping

Passing tests can cite stable requirement IDs, but mappings based on a test title or intent still need review against assertions. Changed/new requirements return to Draft even if an older test mentions the ID. The “Unit Tested >95%” stage name does not mean measured areas exceed 95%.[^1]

## Limits and pending work

The local report excludes hosted PostgreSQL checks, device/emulator testing, Linux golden comparisons, live providers and deployment. It records 89 deferred ruff errors and unresolved security coverage. Backend unit success therefore must not be described as clean API CI or production acceptance.[^1][^2]

An intermittent fixture-request stall was mitigated with test timing/isolation changes but not fully explained. Full scenario reruns and broader journey checks remain useful follow-up work.[^1]

## See also

- [Security](Security.md)
- [Requirements and roadmap](Requirements_and_roadmap.md)
- [Development](Development.md)

## References

[^1]: [Test report, 20 October](../docs/testing/test-report-2026-10-20.md).
[^2]: [Measured coverage report](../docs/coverage/unit-test-coverage.md); [coverage tool](../tools/coverage/report.py).
[^3]: [Test-data plan](../docs/testing/test-data-plan.md); [scenario catalogue](../tools/test-data/scenarios.json).

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
