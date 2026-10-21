# Development

**Development** in Priveo spans a Python API, Flutter mobile app and React portal in one repository. Local configuration, generated artifacts and isolated test storage are important parts of the workflow.[^1]

## Local components

| Component | Setup and execution |
|---|---|
| API | Create a virtual environment in `services/api`, install `.[dev]`, run Uvicorn |
| Mobile | Run `flutter pub get` in `apps/mobile`, then use the dev entry point |
| Portal | Install locked dependencies in `apps/web`, then `npm run dev` |
| Database | Configure a dedicated local database; apply reviewed migrations where intended |

The API project requires Python 3.12 or later. The actual Flutter/Dart constraints and dependency versions are in the mobile manifest; portal commands and versions are in its package file. These manifests are more precise than older stack prose.[^2]

The Android emulator default API address is `http://10.0.2.2:8000`. Mobile dev/prod entry points and Android flavors allow separate installed packages. A build's API address must match the intended environment.[^1]

## Configuration

Local API configuration is read from environment settings and `.env`. Relevant settings include database URL, token secret, administrator credentials and provider keys. Development-only demo credentials and verification-code overrides must remain outside committed source.[^1][^3]

Startup validates hosted environment naming and production requirements. Production rejects development-only configuration and requires suitable secrets/provider configuration. A test passing with mock delivery does not verify the same feature with live credentials.[^3]

## Generated artifacts

| Source change | Follow-up |
|---|---|
| Backend contract | Export OpenAPI, then regenerate dependent clients |
| `docs/brand/tokens.json` | Regenerate mobile and portal theme output |
| Mobile localization source | Regenerate Flutter localization output |
| Data model | Write a reviewed Alembic migration |

The repository conventions name `scripts/export_openapi.py`, `dart run tool/gen_api.dart`, `dart run tool/gen_theme.dart` and `flutter gen-l10n`. The portal theme generator is exposed through its package scripts. CI checks generated output for staleness.[^1][^2]

## Verification workflow

Typical commands are pytest/ruff for the API, `flutter analyze` and `flutter test` for mobile, and portal lint/test/build scripts. Coverage has a dedicated PowerShell runner and report tool. PostgreSQL-specific checks use a disposable cluster script rather than an application database.[^1][^4]

The backend test fixtures can empty the configured test database. `TEST_DATABASE_URL` must never point at a real application database. Synthetic scenario reset commands belong to the guarded fixture tooling; they are separate from production customer imports.[^1][^4]

## Source maintenance

Requirements use stable IDs and owner decisions take precedence over prototype behavior. Current implementation and the dated test report should be checked before relying on a historical handoff's branch, status or test count. Work on this wiki does not apply migrations, seed data or deploy an environment.

## See also

- [Testing](Testing.md)
- [API and data model](API_and_data_model.md)
- [Deployment and hosting](Deployment_and_hosting.md)

## References

[^1]: [Build guide](../docs/build-and-release.md); [repository conventions](../CLAUDE.md), commands and configuration.
[^2]: [API project](../services/api/pyproject.toml); [mobile manifest](../apps/mobile/pubspec.yaml); [portal package](../apps/web/package.json).
[^3]: [Platform configuration](../services/api/app/platform/config.py).
[^4]: [PostgreSQL test script](../services/api/scripts/test_postgres.py); [test-data plan](../docs/testing/test-data-plan.md); [coverage runner](../tools/coverage/run.ps1).

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
