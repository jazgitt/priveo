# 06. Recommendation and roadmap

Version 1.0, 18-Oct-26. Scores are judgments built from docs 01 to 05. They are not measurements.

## 1. Decision matrix

Scale 1 (poor) to 5 (strong). Options: A1 Vercel + Neon Singapore, A2 Vercel + RDS Mumbai + Static IPs, B EC2, C ECS Fargate. Options D, E and the others were rejected in doc 04 and are not scored.

Weights reflect a pre-launch startup: low ops capacity and low cash matter, but customer data and payments make security a first-order item.

| Criterion | Weight | A1 | A2 | B | C | Evidence for the scores |
|---|---|---|---|---|---|---|
| Architecture compatibility | 10 | 4 | 4 | 4 | 5 | A needs media and portal bundling changes. C already has a deploy job and matches `tech-stack.md`; B and C still need the S3 store |
| Security | 15 | 3 | 3 | 4 | 5 | A has a public database endpoint (doc 03). C meets owner checkpoints N1 to N14. B meets them if hardened by hand |
| Reliability | 10 | 4 | 4 | 2 | 4 | B is a single host. Vercel and Fargate replace failed instances |
| Performance (India) | 8 | 3 | 4 | 5 | 5 | A1 has functions and database in Singapore. Round trip to India unmeasured |
| Scalability | 7 | 5 | 5 | 2 | 4 | Vercel scales without action. Fargate needs scaling rules. B is manual |
| Direct cost | 12 | 5 | 3 | 4 | 3 | Doc 05: $36, $145, $54, $138 at 100 DAU |
| Operational effort | 13 | 5 | 4 | 2 | 3 | Doc 05 section 6 |
| Deployment simplicity | 7 | 5 | 4 | 2 | 3 | A works today. C has a partial pipeline. B has none |
| Developer experience | 5 | 5 | 5 | 2 | 3 | Previews, rollback |
| Portability | 8 | 3 | 3 | 5 | 4 | Dockerfile exists. Crons and Blob adapter are Vercel specific |
| Production maturity | 5 | 4 | 4 | 5 | 5 | Python on Vercel is GA; WebSockets, large functions, daemons are beta, and none is needed |
| **Weighted score (out of 5)** | 100 | **4.13** | **3.77** | **3.37** | **4.01** | Sum of weight x score / 100 |

## 2. Sensitivity

| Weight set | A1 | A2 | B | C | Winner |
|---|---|---|---|---|---|
| Base (above) | 4.13 | 3.77 | 3.37 | 4.01 | A1 by 0.12 |
| Security 25 (Ops, Deploy, DX, Cost reduced) | 3.93 | not run | not run | 4.21 | C |
| Cost 25 (Security, Ops, Portability, Maturity reduced) | 4.31 | not run | not run | 3.84 | A1 |
| Ops simplicity 25 (Security, Cost, Portability, Performance reduced) | 4.31 | not run | not run | 3.86 | A1 |

Reading: **A1 and C are close.** The result flips on one question: is a database reachable only over the public internet, and stored outside India, acceptable at launch? The owner's own architecture document says no (`docs/architecture.md:295-323`, checkpoints N2 and N3: RDS not publicly accessible, Fargate and RDS in private subnets). That is a stated requirement, not a weight. Under it A1 and A2 fail the requirement, and C wins. If the owner relaxes the requirement in writing, A1 wins on cost and effort. B never wins.

## 3. Recommendation

1. **Launch architecture: Option C, AWS Mumbai.** One ECS Fargate service (1 vCPU, 2 GB, one task at first, two once real customers depend on it), ALB with an AWS WAF rate rule, RDS PostgreSQL in private subnets, a private S3 bucket with presigned upload and download, EventBridge Scheduler for the cron endpoints, GitHub Actions with OIDC. Portal bundled in the same image so cookies stay same-origin (O1 in doc 01).
2. **Second best: Option A1.** Vercel Pro in `sin1` with Neon Singapore and a private Vercel Blob store. Roughly $36 per month at 100 DAU and almost no operations. Choose it only if the owner accepts the public-database and out-of-India trade-off, and counsel confirms residency is not an issue.
3. **Why C wins.** It is the only option that meets the documented network and data-location design, keeps data in Mumbai, and has an existing deploy job. Its cost premium at 100 DAU is about $70 to $100 per month.
4. **Why the others lose.** A2 pays $100 per month for Static IPs and still has a public database. B saves $80 per month but is a single host with hand patching. D, Cloud Run, Render, Railway and Cloudflare add a platform without solving a problem C leaves open. E breaks `SameSite=Strict` cookies.
5. **Blockers to resolve (any host).**
   - Write the S3 `ObjectStore` (none exists, `store.py:169`).
   - Replace public media URLs with private ones (security backlog finding 3).
   - Set `CRON_SECRET` and wire the eight schedules.
   - Bundle `portal/`, `migrations/` and `alembic.ini` in the image (`Dockerfile:8-16`).
   - Add a migration step to `deploy-aws` (one-off ECS task).
   - Pin dependencies.
6. **Estimated cost at 100 DAU.** C: about $108 (public subnets) to $138 (with NAT), about INR 10,300 to 13,100. Modeled, with Mumbai unit prices unverified. Add Resend, store fees and a staging environment.
7. **Cost evolution (C).** About $244 at 1,000 DAU, $594 at 5,000, $1,119 at 10,000 (doc 05). From 1,000 DAU the largest line is media egress, not compute.
8. **Reconsider or migrate when:**
   - Owner accepts a public database, and operations time becomes the bottleneck: move to A1 or A2.
   - Planner requests regularly exceed 5 minutes: move planning to a separate Fargate task or run-once job.
   - Monthly media egress passes about 1 TB: add CloudFront in front of S3 and thumbnails.
   - Task CPU stays above 60% at peak: add a second task and an autoscaling rule.
   - Uptime requirement above single-AZ RDS: enable Multi-AZ.
   - Neon or Vercel add a Mumbai database and a private route: re-run this matrix.

## 4. Roadmap

| Phase | Work | Effort (estimate) | Exit check |
|---|---|---|---|
| 0. Measure (before spending) | Time `solve_day` on seed data. Measure ortools install size. Count seed customers. Confirm launch society count. Ask counsel about residency | 1 day | Numbers replace the assumptions in doc 05 |
| 1. Make the app host-neutral | S3 `ObjectStore` with presigned PUT and GET; `/v1/public/health` runs `SELECT 1`; security headers; sign-in rate limit hooks; JSON logs; pin dependencies; session expiry | 4 to 6 days | `pytest` and `ruff` pass; upload and download work against a test bucket |
| 2. Container | Dockerfile copies portal, migrations, alembic; HEALTHCHECK; set uvicorn workers; build portal in CI | 1 day | Image serves `/portal/` and `/v1/public/health` locally |
| 3. AWS foundation | Account and MFA, VPC, private subnets, RDS, S3, ECR, ALB, ACM, WAF rule, Secrets Manager, IAM roles. Pick IaC (not chosen yet, `build-plan.md:204`) | 3 to 5 days | Staging stack reachable; RDS not public |
| 4. Pipeline | Extend `deploy-aws`: migration task, smoke test, rollback to previous task definition | 1 to 2 days | Merge to main deploys staging |
| 5. Scheduling | EventBridge schedules for the eight cron endpoints, with bearer token; alarm on 4xx and 5xx from cron | 1 day | Jobs logged once per run; idempotent re-run safe |
| 6. Load and restore tests | Locust run (section 5); RDS restore drill; alarms on CPU, 5xx, DB connections, disk | 2 days | Capacity numbers recorded in this folder |
| 7. Production | Separate account or VPC, production secrets, DNS cutover, mobile `API_BASE_URL` update, store the break-glass runbook | 2 days | Real customer sign-in on production |

Total: about 15 to 20 working days of one engineer. Estimate, not a commitment.

## 5. Load test plan (Locust or k6)

Goal: find the request rate, task size and connection count at which p95 latency leaves target. Do not quote a user count until this is done.

1. Build a workload mix from the router counts: reads on home, calendar and visits (about 70%), writes on skip, pause and support (about 10%), crew upload ticket and confirm (about 10%), sign-in (about 5%), admin portal queries (about 5%).
2. Seed one society with realistic customers and a week of visits. Use a staging copy, never an application database.
3. Ramp to 1, 5, 10, 25, 50 req/s. Hold each step for 5 minutes. Record p50, p95, p99, error rate, task CPU and memory, DB connections, DB CPU.
4. Planner test: call the admin plan route for a week and a month on seed data. Record duration and CPU per society. Run it while the read mix is running.
5. Spike test: a 10x jump for 60 s to mimic a push to all customers.
6. Soak test: 2 hours at 50% of the best step to look for memory growth.
7. Sign-in and code endpoints: verify the WAF rule blocks above the limit and does not block normal use.
8. Pass criteria to set before the run, for example p95 under 500 ms at planned peak, error rate under 0.5%, task CPU under 60%.
9. For Vercel (if chosen later): repeat on a preview deployment to measure cold-start time with OR-Tools and function duration.

Minimum Locust skeleton (do not run against production):

```python
from locust import HttpUser, task, between

class Customer(HttpUser):
    wait_time = between(5, 20)

    def on_start(self):
        r = self.client.post("/v1/identity/login", json={"email": "...", "password": "..."})
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    @task(7)
    def home(self):
        self.client.get("/v1/customer/home", headers=self.headers)
```

Route names above are placeholders. Read the OpenAPI contract in `packages/api-contract/openapi.json` before writing the real script.

## 6. Portability improvements worth doing on any host

- S3-compatible `ObjectStore` behind the existing interface.
- Config for the cron trigger in one place, not only in `vercel.json`.
- Health check with a DB probe.
- Pinned dependencies and a lockfile.
- Migrations as a separate command (already in CI), never on app start.
- Optional later: an API base URL variable in the portal if it ever moves to another origin.

## 7. Owner decisions and open questions

**Decided (owner, 19-Oct-26):** a database with a public endpoint is not acceptable. Options A1 and A2 fail this requirement, so Option C is the launch architecture. A1 stays only as a documented fallback if the owner reverses this.

Open:
1. How many societies and customers at launch and in 12 months?
2. Does counsel require India-only storage of customer data?
3. Is one task acceptable at launch, or must the service survive a task failure with no gap?
4. Which IaC tool, if any?
