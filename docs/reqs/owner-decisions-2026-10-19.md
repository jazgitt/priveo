# Owner decisions: 19 October 2026

1. Product analytics and session replay use PostHog Cloud in the EU region. PostHog has no India region.
2. Session replay is off in release builds (`POSTHOG_REPLAY=false`). It is switched on only after the usage-data notice and switch (`AUTH-18`, `SET-05`) are in the app and masking has been checked on real devices.
3. Hosting: a database with a public endpoint is not acceptable. The launch architecture is AWS Mumbai with ECS Fargate and a private RDS (see `docs/hosting-assessment/`).

4. The admin web portal also uses PostHog EU, in the same project as the app (`ADM-ACC-15`). Autocapture is off and recording is off at release.

5. Session replay in the mobile app records every role: customer, crew and admin. Nobody is excluded. Sign-in screens are recorded too.

6. Replay masks nothing for now, in the app and the portal: text, images, inputs and touches are all recorded. Only password fields stay hidden, as both SDKs always do, and request and response bodies are not recorded. What to mask is to be decided later. Until then, recordings show customer names, mobile numbers, addresses, vehicle numbers, photos and payment details, and they are stored in PostHog EU, outside India. Release builds keep replay off (`POSTHOG_REPLAY=false`), so only test builds record. The open legal question on storing customer data outside India applies before replay is ever switched on for real customers.

Not yet decided: whether usage data needs opt-in before any tracking, instead of the notice and opt-out switch used now (`AUTH-18`, `SET-05` are marked Derived), and whether admin users need their own switch.
