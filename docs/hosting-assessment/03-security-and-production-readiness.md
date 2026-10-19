# 03. Security and production readiness

Version 1.0, 18-Oct-26. Threat model: public mobile and web clients, customer personal data (name, mobile, address, vehicle), manual UPI payments (no card data stored), staff accounts with strong roles, photos of customers' cars.

## 1. Current state (from the repo)

| Area | State | Evidence | Gap |
|---|---|---|---|
| Authentication | Email code then password for customers, mobile and password for crew, user ID and password for admin. Argon2. DB-backed lockouts | `identity/service.py:48,396` | Customer and crew sessions never expire (`security-backlog.md` finding 7) |
| Tokens | HS256 JWT, 15 min, bound to a DB session; refresh token stored hashed | `identity/tokens.py`, `config.py:20` | One shared `TOKEN_SECRET` signs tokens, CSRF and media URLs. Rotation logs everyone out |
| Web session | httpOnly, Secure, `SameSite=Strict` cookie plus CSRF header | `platform/websession.py:29-31` | Strong, but requires same-origin deployment |
| CORS | None configured | `main.py` | Correct for same-origin. Needed only if portal moves to another origin |
| Rate limiting | None at HTTP layer | `main.py` | Add WAF rule on sign-in (finding 4) |
| Security headers | None | `security-backlog.md` finding 6 | Add HSTS, nosniff, frame, CSP |
| Secrets | Environment only; prod refuses mock settings and short `TOKEN_SECRET`; `CRON_SECRET` required in prod | `platform/config.py:106` | `CRON_SECRET` unset on dev, so crons return 503 |
| Media | Public, permanent Blob URLs; declared content type only | `media/store.py:104`, `media/service.py:23` | High finding 3. Needs private bucket and short-lived signed URLs |
| Logging | Plain stdlib logging, request ID returned | `platform/middleware.py:7` | No sensitive-data scrub review done; no JSON format |
| Health | `/v1/public/health` does not check the DB | `system` router | Load balancer would report healthy during a DB outage |
| Dependencies | Unpinned, no lockfile | `pyproject.toml` | No reproducible patching. Add pins and a scanner |
| Docs and OpenAPI | Swagger and ReDoc disabled | `main.py` | Good |

## 2. Controls by hosting option

| Control | Vercel Pro (A) | AWS ECS Fargate (C) | AWS EC2 (B) |
|---|---|---|---|
| TLS | Managed | ACM on ALB or CloudFront | ACM on ALB, or Caddy on host |
| DDoS | Included at the edge | Shield Standard is automatic; WAF is extra | Same as C |
| Rate limiting | Firewall rate limit, $0.55 per million allowed requests (bom1) | WAF rate-based rule (price unverified in this session) | WAF, or nginx limit |
| Database network | **Public endpoint**, password and TLS. Static IPs $100 per month restrict to a shared egress pool | Private subnets, RDS not public (matches `architecture.md` N2, N3) | Same as C |
| Secrets | Project env vars. OIDC available | Secrets Manager (N4 in `architecture.md`) | Same, plus host hardening |
| Least-privilege identity | Blob via OIDC token; no IAM role for the app | Task role limited to one bucket and secrets | Instance role |
| Patching | Vercel patches the runtime. You patch Python deps | Base image rebuilds; you patch the image | You patch OS, Docker, deps |
| Preview access to prod data | Risk: previews inherit variables unless scoped | Separate accounts or VPCs (open item in `architecture.md:320`) | Same |
| Audit and logs | Runtime logs, limited retention (unverified) | CloudWatch, CloudTrail | Same |
| Backups | Depends on database vendor | RDS automated backups on, PITR (`tech-stack.md:57-65`) | Same |

## 3. Data residency

India is the market. Hosting in Mumbai is preferred. Notes:

- Vercel can run compute in `bom1`. Neon cannot host in Mumbai, so a Neon database would sit in Singapore. Customer personal data would then be stored outside India.
- Whether the Digital Personal Data Protection Act requires in-country storage for this data is a legal question. **Unverified here. Ask counsel.**
- RDS and S3 in `ap-south-1` keep data in Mumbai.

## 4. What is not a problem

- A public API is not inherently unsafe. Every route is behind `require_role`, and sessions are server-checked.
- Putting the API in a private subnet behind an ALB is not a defence for the API itself. It protects the database and the tasks.
- No card data is stored, so PCI scope is minimal.

## 5. Required controls before launch, any host

1. Private media with signed URLs, 5 to 15 min expiry. Content-type sniffing on confirm.
2. `CRON_SECRET` set, and schedulers wired.
3. WAF or equivalent rate limit on all sign-in and code endpoints (30 requests per IP per 15 min, as in the backlog).
4. Security headers (HSTS, nosniff, frame-ancestors, CSP for the portal).
5. Health check that runs `SELECT 1`.
6. Pin dependencies; add `pip-audit` or similar in CI.
7. Customer and crew session expiry.
8. Separate secrets and database per environment. Previews cannot read prod.
9. Restore test and alarm set (Phase 8 in `build-plan.md`).
10. JSON logs; confirm no mobile number, email, token or UPI reference is logged.

## 6. Incident basics

- Rotating `TOKEN_SECRET` invalidates all sessions and media links. Document it as the break-glass step.
- Crew passwords are shown to the admin once; no SMS or WhatsApp (CLAUDE.md). Keep that on any host.
- Keep one named owner with access to cloud root credentials and enable MFA.
