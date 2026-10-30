# Deployment and hosting

**Deployment and hosting** cover Priveo's development environments, selected launch architecture and mobile release pipelines. The 19 October owner decision selects AWS Mumbai with ECS Fargate and private RDS and rejects a public database endpoint for launch.[^1]

## Current hosting

Since 29 Oct 2026 the API runs as two Vercel projects in one Pro team, `priveo-api-test` and `priveo-api-prod`, both in Mumbai (`bom1`). Each has its own Supabase PostgreSQL database in Mumbai. The old single `priveo-api` project and its Neon database were retired on 30 Oct 2026. AWS Mumbai with a private RDS remains the later target.[^1][^2]

| | Test | Production |
|---|---|---|
| Deploys | Every merge to `main` | A `v*` tag or a manual run, after a reviewer approves |
| Database | Supabase test project | Supabase prod project |
| Demo logins | Seeded | Absent; startup refuses them |
| Photos | Public Vercel Blob store | Private Vercel Blob store, streamed by the API through signed links |
| Address | `priveo-api-test.vercel.app` | `priveo-api-prod.vercel.app` |

Settings live in the GitHub Environments `test` and `production` and in each Vercel project's own variables. Runtime database access uses Supabase's transaction pooler; migrations use the session pooler through `MIGRATION_DATABASE_URL`, because GitHub runners cannot reach the IPv6-only direct address. Secrets such as the Blob token are stored as Sensitive. Local development uses a local PostgreSQL and never a hosted database. Production `v0.1.0` has been released and smoke-tested with the admin login only; it holds no real data, and email sign-in and photo upload there are not yet exercised. Custom domains are not set up.[^2]

The hosting assessment considers alternatives and documents the trade-offs behind private-database AWS hosting. Its cost figures are estimates with unverified unit-price assumptions; they are not current provider quotes or measured product capacity.[^3]

## Selected AWS direction

The intended deployment uses ECS Fargate, RDS PostgreSQL in private networking, S3 media and EventBridge scheduling in Mumbai. Supporting work includes image packaging, migration execution, secrets, IAM, monitoring, recovery and provider integration.[^1][^3]

The assessment identifies launch blockers including a private S3 object store, expiring media reads, scheduling configuration, packaging portal/migrations in the API image, an AWS migration step and dependency pinning. Infrastructure diagrams and workflow definitions should not be treated as proof these resources are live.[^3]

## Pipelines

| Pipeline family | Role |
|---|---|
| API CI | Lint, tests, PostgreSQL checks and contract freshness |
| Mobile CI | Generated files, analysis and tests |
| Web CI/E2E | Portal lint/build/unit and browser validation |
| API deploy | Test on every merge to `main`; production on a `v*` tag after approval; migrate, seed, deploy and smoke check |
| Mobile integration | Android emulator/live API role checks |
| Android release | Signed bundle and Play internal testing when configured |

Workflow behavior depends on path triggers, repository variables and secrets. A configured file can skip deployment when required settings are absent. Current definitions under `.github/workflows` are authoritative for exact triggers.[^2][^4]

## Scheduled work

The backend exposes eight authenticated internal jobs. Deployment must supply `CRON_SECRET`, arrange host invocation and monitor errors. Billing generation, overdue handling, reminders, freezes, automatic planning and crew society moves should not be assumed timely simply because their code exists.[^5]

## Mobile release

Android has dev and prod flavors. `apps/mobile/tool/build_release.sh` builds an app against the test or production API and names the file `priveo-test-<version>` or `priveo-release-<version>` (see [Development](Development.md)); Settings > Version in the app shows the environment, build and API address. An iOS phone build waits on an Apple Developer account; only simulator builds exist. Production signing and Play delivery require keystore and service-account configuration and initial store setup. The build guide records iOS work as pending at its checkpoint; newer store/device evidence is needed before claiming iOS release readiness.[^2]

The security backlog records fallback to debug signing without a release keystore as an open issue. The latest local test report did not deploy or test real devices, emulators, live providers or hosted PostgreSQL.[^6][^7]

## See also

- [Architecture](Architecture.md)
- [Security](Security.md)
- [Notifications](Notifications.md)

## References

[^1]: [Owner decisions, 19 October](../docs/reqs/owner-decisions-2026-10-19.md), hosting decision.
[^2]: [Build and release guide](../docs/build-and-release.md).
[^3]: [Hosting assessment](../docs/hosting-assessment/README.md); [recommendation and roadmap](../docs/hosting-assessment/06-recommendation-and-roadmap.md).
[^4]: [Workflow directory](../.github/workflows/).
[^5]: [Cron implementation](../services/api/app/notifications/cron.py).
[^6]: [Security backlog](../docs/security-backlog.md), Android finding.
[^7]: [Test report, 20 October](../docs/testing/test-report-2026-10-20.md), exclusions.

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 30 October 2026. Requirements, implementation and verification may have different status.*
