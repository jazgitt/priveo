# 02. Vercel Pro compatibility

Version 1.0, 18-Oct-26. All Vercel facts were fetched from vercel.com docs on 18-Oct-26 (sources at the end). Anything not found in those pages is marked **Unverified**. Classes: Compatible, Compatible with changes, Limitation, Blocker, Not applicable, Unverified.

**Headline.** Vercel Pro can run this API as it is written. The Python runtime is generally available, FastAPI is detected, functions can run up to 800 s, and Mumbai (`bom1`) is a compute region. The real problem is not the compute. It is the database path: Neon has no Mumbai region, and Vercel functions have no private route to a database in your own AWS network unless you pay for Static IPs (a shared pool, not private networking). That conflicts with the owner's own network checkpoints N1 to N14 in `docs/architecture.md:295-323`. It is a requirement mismatch, not a technical blocker.

## 1. The 27 items

| # | Item | Class | Finding and evidence | Severity | Workaround, effort, cost |
|---|---|---|---|---|---|
| 1 | Python runtime and versions | Compatible | 3.12 (default), 3.13, 3.14. App needs `>=3.12` (`pyproject.toml`) | Low | None needed |
| 2 | FastAPI / ASGI | Compatible with changes | Entry file under `app/` named `main.py` with top-level `app` is auto-detected; `main.py:70` defines `app`. The app also serves `/portal` from disk (`webauth/portal.py:15`), which must be bundled | Low | Build portal into `services/api/portal` as `api-deploy.yml` already does. 0.5 day. $0 |
| 3 | Dependency packaging, native libs, size | Unverified | Python limit is 500 MB uncompressed (5 GB in large-functions beta). `ortools`, `reportlab`, `psycopg[binary]` are native wheels. Bundle size not measured. No lockfile | Medium | Pin deps, measure, use `excludeFiles` for tests. 0.5 day. $0 |
| 4 | Memory and CPU | Compatible | Pro default 2 GB / 1 vCPU, max 4 GB / 2 vCPU. Solver uses 1 worker (`solver.py`) | Low | None |
| 5 | Max duration | Limitation | Pro: 300 s default, 800 s max, 1800 s beta. A weekly plan is about 70 s per society and a monthly plan about 300 s per society (calculated from `max_seconds=10` x days; not measured). Multi-society monthly plans can exceed 300 s | Medium | Set `maxDuration` 800 on the plan routes, or run the planner per society, or move to a daemon/worker. 1 day. $0 |
| 6 | Cold starts, Fluid compute | Unverified | Fluid is default for new projects. Import time with OR-Tools unmeasured | Medium | Measure; keep warm via crons is not needed on Fluid. 0.5 day |
| 7 | Request/response payload | Compatible with changes | 4.5 MB cap on function request and response bodies. `LocalObjectStore` passes the whole body through the API (`media/router.py:74-117`), and photos go to 10 MB, video to 25 MB. `BlobObjectStore` uses direct client upload, which avoids this. PDF invoices are small | High if local store used | Use direct-to-storage upload only. Downloads of large private media need signed URLs, not a function proxy. Already partly built. 1 to 2 days |
| 8 | Streaming and SSE | Not applicable | None in code. Python streaming is supported | None | None |
| 9 | Persistent WebSockets | Not applicable | None in code (`architecture.md:360` chose polling first). WebSockets are public beta, Python from 23-Jul-26, and each connection ends at max duration | Low | Revisit if realtime is needed |
| 10 | Background and post-response tasks | Not applicable | No `BackgroundTasks`, threads or Celery in `services/api/app` | None | None |
| 11 | Queues, Workflow, Cron, Daemons | Compatible (Cron). Others not applicable | Pro cron: up to 100 jobs, per-minute precision. The eight jobs map one to one. Daemons are public beta, production only. Queues and Workflow are not used | Low | Add finer schedules now that Pro allows them. Set `CRON_SECRET`. 0.5 day |
| 12 | Concurrency and autoscaling | Compatible | Auto-scales to 30,000 on Pro. The real cap is database connections. Firewall rate limiting exists and bills $0.55 per million allowed requests (bom1) | Low | Rate-limit sign-in (security backlog finding 4). 0.5 day |
| 13 | PostgreSQL connections | Compatible with changes | `NullPool` and `prepare_threshold=None` (`db.py:60`) fit serverless and poolers. Each request opens a new connection, so a pooled endpoint is required. Functions share 1,024 file descriptors | Medium | Use a pooled connection string (Neon pooler, RDS Proxy, or PgBouncer). 0.5 day |
| 14 | Network, outbound, DB latency | Limitation | Outbound IPs are dynamic by default. Static IPs cost $100 per month per project plus Private Data Transfer ($0.187 per GB in bom1) and use a shared pool. They are not supported with the extended-duration or large-function betas | High | Either accept a TLS-and-password-only database, or pay for Static IPs, or host the database where Vercel can reach it privately (Enterprise Secure Compute, not priced here) |
| 15 | Regions, Mumbai | Compatible | `bom1` (ap-south-1) is a compute region. Dev uses `sin1` (`vercel.json`). Neon offers no Mumbai region (neon.com regions page). So the DB would be in Singapore, or RDS in Mumbai | Medium | Function in `sin1` beside Neon, or `bom1` beside RDS. Round-trip time between the two is unmeasured |
| 16 | Local filesystem | Unverified | Not stated in the fetched pages. The app's local media default is `$TMP/priveo-media` (`store.py`), so it is not persistent in any serverless host | Medium | Never use the local store in production. Already the plan |
| 17 | Image and video behavior | Compatible | No server-side processing in the app, so nothing to move | Low | None |
| 18 | Large uploads, direct-to-storage | Compatible with changes | Blob client uploads have no data-transfer charge and files can be up to 5 TB. Private Blob stores are GA. The current store issues public URLs | High (security) | Switch `BlobObjectStore` to a private store with signed GET URLs, or write the S3 store. 2 to 3 days |
| 19 | Deployment size, build limits | Unverified | Build time and size caps were not in the fetched pages. Builds cost $0.007 per minute on Basic machines for paid teams | Low | Check on first deploy |
| 20 | Env vars and secrets | Compatible | Standard project variables. With Fluid, `AWS_EXECUTION_ENV` and other Lambda variables are hidden. `config.py:64` also checks `VERCEL`, so hosted detection still works | Low | None |
| 21 | Preview and production isolation | Compatible with changes | Preview deployments share the project's variables unless scoped. Previews must never get the production `DATABASE_URL` | Medium | Scope variables per environment, separate database. 0.5 day |
| 22 | Domains, HTTPS, CORS, routing | Compatible | Same-origin portal means no CORS is needed (O1 in doc 01) | Low | None |
| 23 | Security controls | Compatible with changes | DDoS protection and WAF with rate limiting are available. App has no rate limit and no security headers | Medium | Add rules and headers. 1 day |
| 24 | Observability | Limitation | Runtime logs are available. App logs are plain text (`priveo.api`). Observability Plus is $1.20 per million events. No metrics or tracing in code | Low | Add JSON logging and a health check that touches the DB. 1 day |
| 25 | Rollback and recovery | Compatible | Instant rollback and promotion exist. Alembic migrations are not run by the app and are not rolled back with a deployment | Medium | Keep migrations backward compatible, run them from CI |
| 26 | Lock-in and portability | Limitation (moderate) | App is plain ASGI and has a Dockerfile, which keeps exit cheap. Crons live in `vercel.json`. Blob adapter is Vercel-specific | Low to medium | Keep the S3 store behind the `ObjectStore` interface |
| 27 | Usage-based billing and overage | Limitation | Pro platform fee $20 per month including 1 seat and $20 usage credit. Extra seats $20. Spend-management notification defaults to $200 per cycle; it notifies, it does not stop spend unless an action is configured | Medium | Set a hard budget action. 10 minutes |

## 2. Blockers

None is an absolute technical blocker for the code as written.

Two conditions block the Vercel option from meeting the owner's stated security design:

1. **Database reachability** (item 14). No private route to RDS in a Mumbai VPC on Pro. Static IPs ($100 per month) restrict by shared egress IP only.
2. **Public media** (item 18). Must be moved to private storage regardless of host.

## 3. Platform facts used (fetched 18-Oct-26)

| Fact | Value | Source |
|---|---|---|
| Max duration, Pro | 300 s default, 800 s max, 1800 s beta | https://vercel.com/docs/functions/limitations |
| Memory, Pro | 2 GB default, 4 GB / 2 vCPU max | same |
| Python bundle | 500 MB uncompressed; 5 GB large functions beta | same, and https://vercel.com/docs/functions/runtimes/python |
| Payload cap | 4.5 MB request or response | same |
| Concurrency | up to 30,000 on Pro | same |
| Python versions | 3.12 default, 3.13, 3.14 | https://vercel.com/docs/functions/runtimes/python |
| Cron | Pro: 100 jobs, per-minute | https://vercel.com/docs/cron-jobs/usage-and-pricing |
| WebSockets | public beta; Python since 23-Jul-26 | https://vercel.com/kb/guide/do-vercel-serverless-functions-support-websocket-connections |
| Daemons | public beta, production only | https://vercel.com/docs/daemons |
| Regions | `bom1` is ap-south-1, Mumbai | https://vercel.com/docs/regions |
| bom1 prices | Active CPU $0.14 per hour; memory $0.0116 per GB-hour; Blob storage $0.025 per GB; Blob transfer $0.067 per GB; Fast Data Transfer $0.20 per GB; CDN requests $2.20 per million | https://vercel.com/docs/pricing/regional-pricing/bom1 |
| Pro plan | $20 per month, includes $20 credit and 1 seat; Flat Rate CDN base tier 1M requests and 1 TB | https://vercel.com/docs/plans/pro-plan |
| Static IPs | $100 per month per project plus Private Data Transfer; shared pool | https://vercel.com/docs/networking/static-ips |
| Private Blob | GA; served through a function or presigned URL | https://vercel.com/docs/vercel-blob/private-storage |
| Neon regions | no Mumbai | https://neon.com/docs/introduction/regions |

Not found in the fetched pages: price per million invocations in bom1, build time limits, filesystem rules, Secure Compute price. These are treated as Unverified.
