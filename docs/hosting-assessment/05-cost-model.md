# 05. Cost model

Version 1.0, 18-Oct-26. Three kinds of number appear. Each is labeled.

- **Verified**: read from an official page on 18-Oct-26 (source in section 8).
- **Modeled**: calculated from verified prices and a stated workload assumption.
- **Unknown**: price not found. A formula or range is given. Replace with a value from the AWS Pricing Calculator before committing money.

**Exchange rate.** USD 1 = INR 95 (modeled). Trackers showed 94.84 on 08-Sep-26 and 95.95 on 16-Sep-26. No October 2026 quote was found, so 95 is a round figure inside that band. Prices exclude GST and other taxes.

## 1. Workload model (assumptions, not measurements)

DAU is not concurrency. Concurrency below is derived from the call rate.

| Driver | Per 100 DAU | Basis |
|---|---|---|
| Sessions per user per day | 2.5 | Assumption |
| API calls per session | 20 | Assumption. Web polls 30 s, mobile refreshes on foreground |
| API calls per month | 150,000 | 100 x 2.5 x 20 x 30 |
| Active CPU per call | 80 ms | Assumption. Measure with Locust |
| Wall time per call | 150 ms | Assumption |
| Peak-hour share of daily calls | 20% | Assumption |
| Peak request rate | 0.28 req/s | 5,000 calls/day x 20% / 3,600 |
| Photos uploaded per month | 6,000 | 0.5 visits per DAU per day x 4 photos x 30 |
| Average photo size | 1.5 MB (limit is 10 MB) | Assumption |
| New media stored per month | 9 GB | 6,000 x 1.5 MB |
| Media egress per month | 27 GB | each photo viewed 3 times |
| Planner CPU | 70 s per society per day | 7 days x `max_seconds=10` (`solver.py:50`), upper bound |
| Builds | 30 per month | Assumption |

| Scenario | DAU | Calls per month | Peak req/s | Concurrent requests at peak (req/s x 0.15 s) | Societies (assumed) | Media stored at month 12 | Media egress per month |
|---|---|---|---|---|---|---|---|
| 1 | 100 | 150,000 | 0.28 | 0.04 | 1 | 108 GB | 27 GB |
| 2 | 1,000 | 1.5 million | 2.8 | 0.4 | 3 | 1,080 GB | 270 GB |
| 3 | 5,000 | 7.5 million | 14 | 2.1 | 10 | 5,400 GB | 1,350 GB |
| 4 | 10,000 | 15 million | 28 | 4.2 | 20 | 10,800 GB | 2,700 GB |

Spiky real traffic (a push notification sent to everyone, 8 PM schedule freeze) can be 10 to 50 times the average. Not modeled.

## 2. Verified unit prices

| Item | Price | Source |
|---|---|---|
| Vercel Pro platform fee | $20 per month; includes 1 seat and $20 usage credit; extra seat $20 | pro-plan page |
| Vercel bom1 Active CPU | $0.14 per hour | regional pricing bom1 |
| Vercel bom1 provisioned memory | $0.0116 per GB-hour | same |
| Vercel bom1 Blob storage | $0.025 per GB | same |
| Vercel bom1 Blob data transfer | $0.067 per GB | same |
| Vercel bom1 firewall rate limit | $0.55 per million allowed requests | same |
| Vercel bom1 Fast Data Transfer | $0.20 per GB (Pro includes a Flat Rate CDN base tier of 1M requests and 1 TB) | same, pro-plan page |
| Vercel Static IPs | $100 per month per project, plus $0.187 per GB Private Data Transfer (bom1) | static-ips, bom1 |
| Neon Launch compute | $0.106 per CU-hour; storage $0.35 per GB-month; 7-day history | neon.com/pricing |
| AWS Fargate Linux x86 (US East N. Virginia, **not Mumbai**) | about $0.0405 per vCPU-hour and $0.0044 per GB-hour | aws fargate pricing page |
| AWS ALB (US East) | $0.0225 per hour; $0.008 per LCU-hour | elasticloadbalancing pricing page |
| AWS NAT gateway | $0.045 per hour; $0.045 per GB processed | vpc pricing page |
| AWS public IPv4 | $0.005 per hour per address | vpc pricing page |

## 3. Unknown prices

| Item | Handling |
|---|---|
| Fargate, ALB in Mumbai | Modeled with US East list price. Mumbai may differ. Treat results as plus or minus 25% |
| RDS Postgres Mumbai instance, storage, backups | Modeled at $20, $35, $70, $140 per month by tier (db.t4g.micro, small, medium, then Multi-AZ). **Unknown. Check the calculator** |
| WAF (web ACL, rules, requests) | Modeled at about $9 to $17 per month. **Unknown** |
| S3 and CloudFront India | Modeled at $0.025 per GB-month and $0.11 per GB egress. **Unknown** |
| CloudWatch, Secrets Manager | Modeled at $3 to $25 and $2 per month. **Unknown** |
| Vercel price per million invocations | Not on the bom1 page. Modeled at $0.60 per million. **Unknown** |
| Resend plan, FCM, Apple and Google fees, Sentry | Outside hosting. Not priced |
| EC2 t4g in Mumbai | Modeled at $17 (small) and $34 (medium) per month. **Unknown** |
| Cloud Run, Render, Railway | Not priced; pages did not load. Rejected for other reasons |

## 4. Compute formulas

- Vercel Active CPU = calls x 0.08 s / 3,600 x $0.14
- Vercel memory = calls x 0.15 s x 2 GB / 3,600 x $0.0116
- Vercel bill = $20 + max(0, usage - $20), plus seats
- Fargate task per month = (vCPU x 0.0405 + GB x 0.0044) x 730
- ALB per month = 0.0225 x 730 + LCU x 0.008 x 730 (about $16.4 + $5.8 per LCU)
- NAT per month = 0.045 x 730 = $32.9, plus $0.045 per GB

## 5. Monthly cost by option (USD, modeled unless noted)

### A1. Vercel (sin1) + Neon Singapore + Vercel private Blob

| Line | 100 DAU | 1,000 | 5,000 | 10,000 |
|---|---|---|---|---|
| Vercel Active CPU | 0.47 | 4.67 | 23.3 | 46.7 |
| Vercel memory | 0.15 | 1.45 | 7.25 | 14.5 |
| Invocations (unknown rate) | 0.09 | 0.90 | 4.5 | 9.0 |
| Planner CPU | 0.08 | 0.25 | 0.84 | 1.7 |
| Usage subtotal | 0.8 | 7.3 | 35.9 | 71.9 |
| Platform bill (fee $20, credit $20) | 20 | 20 | 35.9 | 71.9 |
| Firewall rate limit | 0.1 | 0.8 | 4.1 | 8.3 |
| Neon (0.25, 0.5, 2, 4 CU; 5, 10, 30, 60 GB) | 11 | 42 | 165 | 330 |
| Blob storage + transfer | 4.5 | 45 | 226 | 451 |
| **Total USD** | **36** | **108** | **431** | **861** |
| Total INR at 95 | 3,400 | 10,300 | 40,900 | 81,800 |

### A2. Vercel (bom1) + RDS Mumbai (public, allow-listed to Static IPs)

Same as A1 except: Neon replaced by RDS (20, 35, 70, 140), Static IPs +100, Private Data Transfer at 30 KB per call (0.8, 8.4, 42, 84).

| | 100 | 1,000 | 5,000 | 10,000 |
|---|---|---|---|---|
| **Total USD** | **145** | **209** | **478** | **855** |
| Total INR at 95 | 13,800 | 19,900 | 45,400 | 81,200 |

### B. EC2 + RDS + S3 (single host at 100 DAU; two hosts at 1k; not modeled above that)

| | 100 | 1,000 |
|---|---|---|
| EC2 + EBS | 19 | 70 |
| ALB + 2 IPv4 (from 1k); at 100, Caddy on host plus 1 IPv4 | 4 | 30 |
| RDS | 20 | 35 |
| Logs, secrets | 5 | 7 |
| Media (S3 + egress) | 6 | 57 |
| **Total USD** | **54** | **199** |
| Total INR at 95 | 5,100 | 18,900 |

### C. ECS Fargate + ALB + RDS + S3

| Line | 100 | 1,000 | 5,000 | 10,000 |
|---|---|---|---|---|
| Fargate (1x 1vCPU/2GB; 2x 1/2; 2x 2/4; 4x 2/4) | 36 | 72 | 144 | 288 |
| ALB incl. LCU | 22 | 24 | 30 | 40 |
| Public IPv4 for ALB (2 AZ) | 7 | 7 | 7 | 7 |
| NAT gateway (1 AZ) | 33 | 33 | 33 | 33 |
| RDS | 20 | 35 | 70 | 140 |
| WAF | 9 | 9 | 13 | 17 |
| CloudWatch, Secrets Manager | 5 | 7 | 14 | 27 |
| S3 + egress | 6 | 57 | 283 | 567 |
| **Total USD** | **138** | **244** | **594** | **1,119** |
| Total INR at 95 | 13,100 | 23,200 | 56,400 | 106,300 |
| Without NAT (tasks in public subnets) | 108 | 214 | 564 | 1,089 |

## 6. Reading the numbers

1. **At 100 DAU the compute is almost free on every host.** The choice is about fixed costs. Vercel with Neon is about $36. Fargate is about $108 to $138. The gap is mostly the ALB, NAT, WAF and RDS.
2. **Vercel's advantage disappears when the database must be in Mumbai and not public.** A2 costs about the same as C at 100 DAU and has a weaker network design.
3. **Media egress becomes the largest line from about 1,000 DAU** on every host. Cut it by serving thumbnails, compressing on the phone, and caching on device. The photo size and view-count assumptions are untested and swing this line by several times.
4. **The scheduler is not a cost issue** (under $2 per month on Vercel) but it is a duration and sizing issue (doc 02, item 5).
5. **Staging.** A second Fargate environment costs roughly 40% to 70% of production (smaller task, no WAF, shared NAT is not possible across accounts). Vercel preview deployments are covered by usage. Neon branches cost compute only while active. Not included above.
6. **Operational effort per month (hours, estimate).** A1 about 2, A2 about 3, C about 6 to 8, B about 10 to 15. Multiply by your own hourly cost. The model does not invent one.
7. **Bill-shock risk.** Vercel and S3 egress scale with traffic and attacks. Set a Vercel spend action, an AWS Budget and a WAF rate rule. Fargate with a fixed task count caps compute cost; extra load shows up as slow responses instead of a larger bill, but NAT and ALB data charges still scale.

## 7. Predictable baseline versus growth

| Host | Baseline (100 DAU) | Burst behaviour | Growth shape |
|---|---|---|---|
| A1 | $36 | Auto-scales; bill follows traffic | Steps on Neon size and media |
| C | $108 to $138 | Fixed until you add tasks | Steps with task count and RDS class |

## 8. Sources (accessed 18-Oct-26)

- https://vercel.com/docs/plans/pro-plan
- https://vercel.com/docs/pricing
- https://vercel.com/docs/pricing/regional-pricing/bom1
- https://vercel.com/docs/networking/static-ips
- https://vercel.com/docs/vercel-blob/usage-and-pricing
- https://neon.com/pricing
- https://aws.amazon.com/fargate/pricing/ (US East only visible)
- https://aws.amazon.com/elasticloadbalancing/pricing/ (US East only visible)
- https://aws.amazon.com/vpc/pricing/
- Exchange-rate trackers: https://dollarrupee.in/ and https://longforecast.com/usd-to-inr-forecast-2017-2018-2019-2020-2021-indian-rupee (September 2026 readings; October not available)
