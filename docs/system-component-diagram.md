# Priveo system component diagram

**Updated 31-Oct-2026** from the code on branch `feat/mani-portal-wiring` (migration head 0042). It replaces the Phase 0 diagram, which showed mock repositories and no database. Hosting is the interim setup of 29-Oct-2026 (Vercel and Supabase). The AWS target is in [`architecture.md`](architecture.md).

Solid lines are built in the repository. Dashed lines are configured or planned but not live. The legend at the end says which is which.

```mermaid
flowchart LR
  subgraph Clients[Clients]
    subgraph Mobile[Flutter app - iOS and Android]
      Shells[Role shells via go_router<br/>customer, crew, admin quick actions]
      Features[Feature folders<br/>auth, customer, crew, scheduling,<br/>changes_money, support, people, admin_quick]
      MApi[Generated API client api.g.dart<br/>Dio, bearer token, refresh and retry]
      MStore[Secure storage]
      MAnalytics[PostHog analytics<br/>consent switch for customers]
    end
    subgraph Portal[React admin portal - apps/web]
      Pages[Pages: customers, crew, schedule, payments,<br/>complaints, capacity, settings, audit, Mani]
      Blocks[Shared blocks: useAppMutation,<br/>useConfirm, useTasks - shadcn/ui]
      WApi[Typed API client<br/>HttpOnly cookie and CSRF]
    end
  end

  subgraph Vercel[Vercel project - test or prod, Mumbai bom1]
    subgraph API[FastAPI service - services/api, one deployable]
      Edge[RequestIdMiddleware and error envelope<br/>startup checks]
      Routers[Routers<br/>/v1/auth, /v1/public, /v1/customer, /v1/crew,<br/>/v1/admin, /v1/web, /v1/media, /v1/internal/cron]
      Modules[Domain modules<br/>identity, customers, directory, crew, scheduling,<br/>changes, visits, billing, addons, support,<br/>notifications, media, features, webauth]
      Solver[Scheduler - OR-Tools CP-SAT<br/>scheduling/solver.py, in process]
      ManiMod[Mani Bond agent - app/mani<br/>retrieval, tools, memory, budget]
      Jobs[8 cron jobs<br/>payments, freeze, planning, reminders]
    end
    PortalBuild[Portal build output<br/>services/api/portal, deployed with the API]
  end

  subgraph Data[Data - Supabase PostgreSQL, Mumbai]
    PG[(PostgreSQL<br/>one database per environment)]
    Vec[(pgvector<br/>mani_sources and mani_chunks)]
  end

  subgraph Services[External services]
    Resend[Resend email<br/>codes, welcome, reset]
    Blob[Vercel Blob<br/>photos and documents]
    PostHog[PostHog Cloud EU]
    FCM[FCM push]
    Ollama[Ollama local<br/>qwen3 chat and embedding]
    OpenRouter[OpenRouter<br/>configuration only]
  end

  subgraph Delivery[Build and release]
    GHA[GitHub Actions<br/>api, web, mobile CI and deploy]
    Local[tools/dev/check-local.sh<br/>run-local.sh]
  end

  Shells --> Features --> MApi
  MApi --> MStore
  Features --> MAnalytics
  Pages --> Blocks --> WApi
  MApi <-->|HTTPS JSON, Bearer| Routers
  WApi <-->|HTTPS JSON, cookie and CSRF| Routers
  PortalBuild -. served with .-> WApi
  Routers --> Edge --> Modules
  Modules --> Solver
  Routers --> ManiMod
  Jobs --> Modules
  Modules --> PG
  ManiMod --> PG
  ManiMod --> Vec
  Modules --> Resend
  Modules --> Blob
  Modules -. logging sender today .-> FCM
  MAnalytics --> PostHog
  Pages --> PostHog
  ManiMod --> Ollama
  ManiMod -. config only .-> OpenRouter
  Vercel -. Vercel cron with CRON_SECRET .-> Jobs
  GHA -->|migrate, seed, deploy| Vercel
  GHA -->|migrate and seed| PG
  Local -.-> API
```

## Component responsibilities

| Component | Responsibility |
|---|---|
| Flutter app | One app for customer, crew and the admin quick actions. The role on the login picks the shell. Models and API calls are generated from `packages/api-contract/openapi.json`. Tokens sit in secure storage. |
| React admin portal | Every admin function. Calls the `admin` routes with an HttpOnly cookie and CSRF, a 60-minute inactivity limit. Built into `services/api/portal` and deployed with the API. |
| FastAPI service | One modular monolith. Routers check the caller and call services, services hold the rules. Errors use one envelope (`code`, `message`, `fields`, `request_id`). On start it refuses to run with a missing `TOKEN_SECRET`, a bad `ENVIRONMENT` or dev-only settings in prod. |
| Domain modules | `identity` (logins, blocks, sessions), `customers`, `directory`, `crew`, `scheduling` (the only writer of scheduled visits), `changes` (skip, pause, 9 PM rule), `visits`, `billing` (UPI statuses, Over due, Inactive), `addons`, `support`, `notifications`, `media`, `features` (flags), `webauth`. |
| Scheduler | OR-Tools CP-SAT in the same service. `solve(inputs)` is a pure function. The result is a Draft schedule, frozen at 8 PM the day before. The automatic planner is coded and off by default. |
| Cron jobs | Eight routes under `/v1/internal/cron/`, started by Vercel cron and checked with `CRON_SECRET`: crew society moves, automatic planning, freeze due, payments generate, payments overdue, renewal reminders, check-in notify, complaints overdue. The Mani retention job uses the same route. |
| Mani Bond | Admin-only agent at `/v1/admin/mani`. Hybrid search (vector and words) over the indexed docs and code, ten read-only live data tools, memory, a spending budget and 90-day retention. Local backend is Ollama; OpenRouter is configuration only. |
| PostgreSQL | One Supabase database per environment (test and prod). Alembic migrations written by hand run in the deploy step. The `mani_chunks` table holds `vector(1024)` embeddings. |
| Media | Photos and documents go to Vercel Blob through the API when `BLOB_READ_WRITE_TOKEN` is set, otherwise to a local dev store. |
| Email and push | Resend sends codes and the welcome email; without a key a logging sender is used. Push is a logging sender until FCM is set up. |
| Analytics | PostHog Cloud EU in the app and the portal. Session replay is off in release builds. |
| Delivery | GitHub Actions: `api-ci`, `api-deploy` (test on every merge to `main`; production on a `v*` tag or manual run after approval), `web-ci`, `web-e2e`, `mobile-ci`, goldens, integration, Android release. `tools/dev/check-local.sh` runs the same checks on a Mac. |

## Legend: what is live

| Status | Components |
|---|---|
| Built and running | FastAPI service and modules, PostgreSQL on Supabase (test), portal, Flutter app, scheduler, cron jobs on Vercel, PostHog |
| Built, not yet live | Resend sending (key given, sending-domain verification left), Mani on test or prod (local only for now) |
| Logging stand-in | Push (FCM not connected), media on a local store when no Blob token |
| Planned | AWS Mumbai with a private RDS (ECS Fargate, S3, EventBridge), OpenRouter backend, a gateway or WAF in front of the API |

## Differences from the AWS target

`architecture.md` §2 draws CloudFront, an ALB, ECS, RDS, S3, EventBridge, FCM and Resend. Today the Vercel project replaces the load balancer and ECS, Vercel cron replaces EventBridge, Vercel Blob stands in for S3, and Supabase replaces RDS. The database is reached over TLS and credentials, not from a private subnet, so checkpoints N3 and N5 in `architecture.md` §7.1 are not met yet.
