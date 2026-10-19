# Owner decisions: 19 October 2026

1. Product analytics and session replay use PostHog Cloud in the EU region. PostHog has no India region.
2. Session replay is off in release builds (`POSTHOG_REPLAY=false`). It is switched on only after the usage-data notice and switch (`AUTH-18`, `SET-05`) are in the app and masking has been checked on real devices.
3. Hosting: a database with a public endpoint is not acceptable. The launch architecture is AWS Mumbai with ECS Fargate and a private RDS (see `docs/hosting-assessment/`).

Not yet decided: whether usage data needs opt-in before any tracking, instead of the notice and opt-out switch used now (`AUTH-18`, `SET-05` are marked Derived), and whether admin users need their own switch.
