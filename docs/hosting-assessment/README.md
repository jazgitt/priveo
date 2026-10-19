# Hosting assessment

Version 1.0, 18-Oct-26. Documentation only. No code, infrastructure or deployment was changed.

## Executive summary

Priveo's API can run on Vercel Pro as written. The Python runtime is generally available, functions can run up to 800 seconds, and Mumbai is a compute region. The problem is the database: Neon has no Mumbai region, and a Vercel function has no private route to a database in your own AWS network. The owner's architecture document requires private subnets and a non-public database. On that requirement, **AWS Mumbai with ECS Fargate** is recommended for launch. **Vercel Pro with Neon Singapore** is the second choice and is about $70 to $100 per month cheaper at 100 DAU, if the owner accepts a public database endpoint stored outside India.

**Owner decision, 19-Oct-26: a public-endpoint database is not acceptable. Option C (AWS Mumbai, ECS Fargate, private RDS) is the launch architecture.**

The weighted matrix is close (Vercel 4.13, Fargate 4.01 on base weights). The result flips with the security weight or the stated requirement, so the owner's answer to one question settles it.

## Major findings

1. The portal is same-origin with the API (relative `/v1` fetches, `SameSite=Strict` cookie). Moving it to S3 + CloudFront on another origin breaks sign-in without code changes.
2. There is no S3 store in the code, and media URLs are public and permanent today. Both must change on any host.
3. The scheduler runs inside request threads. A weekly plan is up to about 70 s per society and a monthly plan about 300 s (calculated from `max_seconds=10`; not measured). That fits Vercel's 800 s limit but not its 300 s default for multi-society plans.
4. All eight cron jobs are daily only because of the Hobby plan. Nothing on AWS triggers them yet, and `CRON_SECRET` is unset on dev.
5. At 100 DAU compute is nearly free everywhere. Fixed costs (ALB, NAT, RDS, WAF) decide the bill. From about 1,000 DAU, media egress is the largest cost line.

## Critical blockers (any host)

- Write the S3 `ObjectStore` and move media to private storage with signed URLs.
- Set `CRON_SECRET` and wire the eight schedules.
- Put the portal, migrations and `alembic.ini` into the image, and add a migration step to `deploy-aws`.
- Pin dependencies (there is no lockfile).

## Estimated monthly cost (modeled; Mumbai AWS unit prices unverified)

| DAU | Vercel + Neon SG | Vercel + RDS + Static IPs | EC2 | Fargate (with NAT) |
|---|---|---|---|---|
| 100 | $36 (INR 3,400) | $145 (INR 13,800) | $54 (INR 5,100) | $138 (INR 13,100) |
| 1,000 | $108 | $209 | $199 | $244 |
| 5,000 | $431 | $478 | n/a | $594 |
| 10,000 | $861 | $855 | n/a | $1,119 |

Rate used: USD 1 = INR 95 (modeled from September 2026 readings; no October quote found). Excludes GST, Resend, store fees, staging.

## Documents

1. [01 Current architecture](01-current-architecture.md)
2. [02 Vercel Pro compatibility](02-vercel-pro-compatibility.md)
3. [03 Security and production readiness](03-security-and-production-readiness.md)
4. [04 Hosting alternatives](04-hosting-alternatives.md)
5. [05 Cost model](05-cost-model.md)
6. [06 Recommendation and roadmap](06-recommendation-and-roadmap.md)

## What is not verified

AWS Mumbai prices (Fargate, ALB, RDS, WAF, S3), Vercel invocation price, Vercel build and filesystem limits, OR-Tools bundle size, cold-start time, solver time on real data, customer and society counts, legal data-residency rules, and Render, Railway and Cloud Run pricing and regions. Each is marked in the relevant document.
