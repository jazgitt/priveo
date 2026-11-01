# Mani: stale claims in the indexed documents

Written 1-Nov-26 for the owner. These documents are still indexed by Mani, so it can repeat these claims as current. Nothing here has been edited; the owner will correct them.

## What is current

- Hosting: two Vercel projects (`priveo-api-test`, `priveo-api-prod`, region `bom1`), each with its own Supabase PostgreSQL in Mumbai (`CLAUDE.md` "State of the repo", `services/api/vercel.json`).
- Scheduled jobs: Vercel Cron paths in `services/api/vercel.json`, not EventBridge Scheduler and not ECS tasks.
- The old Neon database and the `priveo-api` project are retired (`wiki/Deployment_and_hosting.md`, 30-Oct-26).
- AWS Mumbai with ECS Fargate and a private RDS is only a later target (owner, 29-Oct-26; the 19-Oct-26 decision stays the later target).
- Mani models (`services/api/app/mani/config.py`): local chat `qwen3:8b`, local embeddings `qwen3-embedding:8b`. No document in the remaining set states a 4k context or a 4b model as current.

## Claims, most misleading first

| File | Line | Claim | Why stale / what is current |
|---|---|---|---|
| `docs/tech-stack.md` | 14 | Hosting is "AWS Mumbai: ECS Fargate for the API, RDS for Postgres, S3 for media, EventBridge Scheduler for cron jobs" and "All choices there are decided" | Current hosting is Vercel + Supabase. AWS is the later target only. |
| `docs/reqs/owner-decisions-2026-10-19.md` | 5 | "The launch architecture is AWS Mumbai with ECS Fargate and a private RDS" | Superseded for now by the 29-Oct-26 decision. AWS is the later target. It also points to `docs/hosting-assessment/`, which is no longer indexed. |
| `wiki/Deployment_and_hosting.md` | 3 | The 19 October decision "selects AWS Mumbai with ECS Fargate and private RDS" for launch | Contradicts its own "Current hosting" section. Launch runs on Vercel + Supabase today. |
| `wiki/Deployment_and_hosting.md` | 21-25 | "Selected AWS direction. The intended deployment uses ECS Fargate, RDS ... S3 media and EventBridge scheduling" | Should read "later target". Media is a local store or Vercel Blob; scheduling is Vercel Cron. |
| `docs/architecture.md` | 29-39 | Diagram: FastAPI service (ECS), RDS, "EventBridge Scheduler -> ECS task" | The service is a Vercel function and the database is Supabase. Cron is Vercel Cron. |
| `docs/architecture.md` | 163 | "EventBridge Scheduler starts the ECS task. Jobs call services, never repositories." | Jobs run from Vercel Cron paths under `/v1/internal/cron/`. |
| `docs/architecture.md` | 304 | N2: "ECS Fargate tasks run in private subnets with no public IP" | A checklist for the later AWS build. Not true of the running system. |
| `docs/architecture.md` | 305 | N3: "RDS has PubliclyAccessible=false and sits in private subnets" | Today's database is a Supabase project with a pooler address. RDS is the later target. |
| `docs/architecture.md` | 307 | N5: "Migrations and seeding run as a one-off ECS task inside the VPC" | Migrations and seeding run from the `api-deploy` workflow against the Supabase database. |
| `docs/architecture.md` | 308 | N6: "GitHub Actions assumes an AWS role by OIDC" | The Vercel jobs use Vercel tokens in GitHub Environments. AWS OIDC applies only if `DEPLOY_PROVIDER=aws`. |
| `docs/architecture.md` | 311 | N9: "EventBridge Scheduler starts tasks inside the VPC" | Vercel Cron calls internal paths. |
| `docs/architecture.md` | 315 | N13: logs and alarms go to CloudWatch (load balancer, WAF, VPC flow logs) | Logs are Vercel runtime logs. No CloudWatch exists. |
| `docs/architecture.md` | 292 | "Config and secrets: Environment variables and AWS Secrets Manager" | Secrets are Vercel and GitHub Environment variables. |
| `docs/architecture.md` | 359 | Scheduler runs in-process; "Move to a separate ECS task later" | Vercel functions are request-bound. The planner is default-disabled and runs from a Vercel Cron path. |
| `docs/architecture.md` | 321-323 | Open: "whether prod uses its own AWS account"; "move dev to AWS too" | Prod is already on Vercel + Supabase. The question applies to the later move only. |
| `docs/architecture.md` | 159 | "Test with realistic volumes before sizing ECS tasks" | There are no ECS tasks. Function size and Supabase plan matter now. |
| `docs/tech-stack.md` | 50 | Background jobs: "AWS EventBridge Scheduler triggering ECS tasks" | Vercel Cron. |
| `docs/tech-stack.md` | 54 | Configuration: "AWS Secrets Manager for keys" | Vercel and GitHub Environment variables. |
| `docs/tech-stack.md` | 60 | "Docker images ... run on ECS Fargate (decided)" | The API is deployed to Vercel. The Dockerfile serves the later AWS target. |
| `docs/tech-stack.md` | 61 | "Database: RDS PostgreSQL, Multi-AZ off in MVP" | Supabase PostgreSQL (Mumbai). |
| `docs/tech-stack.md` | 106 | Portal hosting: "Static build on S3 behind CloudFront, same AWS account" | Check the actual portal hosting. It is not on S3 and CloudFront today. |
| `docs/tech-stack.md` | 87 | "Test with realistic volumes before choosing ECS task sizes" | No ECS tasks. |
| `CLAUDE.md` | 26 | "Tech stack (decided by the owner) ... AWS Mumbai (ECS Fargate, RDS, S3, EventBridge Scheduler) for hosting" | Conflicts with line 7 of the same file. Say "later target" and name Vercel + Supabase as current. |
| `docs/architecture.md` | 299 | The 29-Oct-26 note sits in the middle of the AWS section, so the surrounding N1-N13 table reads as current | Add a heading such as "Later AWS target" above N1 to N13. |
| `docs/build-and-release.md` | 79 | `deploy-aws` job described next to the Vercel jobs | Correct as an optional switch, but a reader may take AWS as live. State that the AWS job is unused. |
| `docs/build-and-release.md` | 90-95 | Variables `DEPLOY_PROVIDER`, `AWS_DEPLOY_ROLE_ARN`, `AWS_REGION`, `ECS_*`, `API_DEV_URL` | Only for `DEPLOY_PROVIDER=aws`. Current environments are `test` and `production` on Vercel. |
| `docs/build-and-release.md` | 148-150 | "AWS (switch with DEPLOY_PROVIDER=aws)": create ECR, ECS Fargate service, load balancer | Unused path. Mark as later target. |
| `docs/security-backlog.md` | 45 | "The AWS network review (N1 to N13 in docs/architecture.md)" as planned security testing | Applies only after the AWS move. Today's review is Vercel + Supabase (Data API off, pooler, Vercel Firewall). |
| `docs/design/admin-portal-ui-review.md` | 148 | "This fits the planned AWS ECS hosting; decide when hosting moves." | Hosting has moved to Vercel. The note is stale. |
| `docs/reqs/admin-functional-requirements.md` | 566 | "an IP allowlist or AWS WAF rules in front of the web portal" | Vercel Firewall is the current tool (`docs/security-backlog.md` line 16). Mark WAF as a later AWS option. |
| `wiki/Architecture.md` | 46 | "private S3 still identified as launch work" | Media is a local store or Vercel Blob. Private S3 belongs to the later AWS move. |
| `wiki/Glossary.md` | 78 | "S3: Planned private object storage for the AWS launch direction" | Say "later AWS target". |
| `wiki/Analytics_and_privacy.md` | 29 | "AWS Mumbai is the selected application-hosting direction" | Current hosting is Vercel (`bom1`) + Supabase (Mumbai). AWS is later. |
| `wiki/README.md` | 53 | "Development hosting, AWS target and release work" | Fine as written, but the linked page leads with AWS as "selected". Fix the page, not this line. |
| `wiki/Deployment_and_hosting.md` | 19 | Hosting assessment "documents the trade-offs behind private-database AWS hosting" | The assessment is historical and no longer indexed. Say so. |
| `docs/testing/test-report-2026-10-20.md` | 43 | Security test gaps listed against a pre-Vercel setup | Report is dated 20-Oct-26. Treat as history, not current state. |
| `docs/agent/agent-architecure.md` | 22 | D1: prod model path "OpenRouter or AWS Bedrock" | Fine as an option. Bedrock is built after the MVP (D16). Keep it labelled as future. |
| `docs/agent/agent-architecure.md` | 225 | Bedrock row with Claude and an India inference profile | Future option only, not built. The row should say "not built". |
| `docs/agent/agent-architecure.md` | 247 | Amazon Transcribe and Polly proposal | Earlier proposal, marked as such. No voice is built. |
| `docs/agent/agent-architecure.md` | 63 | "the earlier plan assumed AWS (RDS, ECS worker, SQS, EventBridge)" | Correctly labelled history. Keep. |
| `docs/agent/agent-architecure.md` | 57 | Local model reality: "7 to 14 billion parameter quantised models" | Accurate. Local chat is `qwen3:8b`. Listed only so nobody reads a 4b/4k limit into it. |

## Notes

- Items from `docs/architecture.md` N1 to N13 are one problem: a later-target checklist written as present tense.
- The last five rows are low risk. They are labelled correctly in context and are listed so the owner can confirm and skip them.
- `docs/hosting-assessment/` and `docs/build-plan.md` are now excluded from the index, so they are not scanned here.
