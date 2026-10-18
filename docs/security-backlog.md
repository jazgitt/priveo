# Security backlog

Source: the security review of 18 Oct 2026 (code read, `npm audit`, git history scan). Findings 1 and 2 are fixed in commit `039a5f3`. Everything below is open and kept for later. Severity is High, Medium or Low.

## Done

| # | Finding | Fix |
|---|---|---|
| 1 | Anyone could lock the admin or a crew login for good with 5 wrong passwords | Timed blocks of 15 minutes, 1 hour, then 24 hours (CRW-ACC-07). The portal also signs out after 60 idle minutes (ADM-ACC-12) |
| 2 | A default `TOKEN_SECRET` and dev mode could run on a hosted server | The server refuses to start without a real secret, without `ENVIRONMENT` set to exactly `dev` or `prod` on a hosted server, and in prod with dev-only settings. No demo logins in prod |

## Open: needs a decision or an action by the owner

| What | Why | Needs |
|---|---|---|
| Rate limit on sign-in by IP address | Finding 4, below. Blocks stop guessing one account, not one password tried on many accounts | Add a Vercel Firewall rule: path starts with `/v1/auth/` or equals `/v1/web/login`, 30 requests per IP per 15 minutes, then deny. The team looked like it is on the Hobby plan, which may not allow it. On AWS use a WAF rate rule |
| `CRON_SECRET` is not set on the dev API | All 8 scheduled jobs answer 503, so payments are not generated or marked overdue and reminders are not sent | `npx vercel env add CRON_SECRET production` with a long random value |

## Open findings

**High**
- **3. Media files are public and permanent.** The Vercel Blob store is public and read URLs never expire (`app/media/store.py`). This covers vehicle photos, number plates, RC documents and complaint photos. Fix: private S3 with short-lived signed URLs, as part of the S3 work.

**Medium**
- **4. No limit per IP address** on `/auth/start`, `/auth/code` and `/auth/login`: one password tried across many crew numbers, account discovery, and Resend cost. See the firewall item above. An API-side limit (table plus migration) is the alternative.
- **5. Crew passwords are guessable.** `generate_password` (`app/crew/service.py`) gives 3 letters of the name, 4 digits and `$`: about 10,000 options. Crew cannot change it. Fix: a longer random password, or let crew change it (the owner decided they cannot, CRW-ACC-06).
- **6. No security headers** on the portal or API: Content-Security-Policy, `frame-ancestors`, `X-Content-Type-Options`, `Referrer-Policy`.
- **7. Customer and crew sessions never expire.** A refresh token works forever, and nothing detects a reused one. Needs an owner decision on the lifetime (AUTH-17, CRW-ACC-11).

**Low**
- **8.** `change_password` (`app/customers/account.py`) does not count wrong current passwords.
- **9.** `start_email_change` has no send limit.
- **10.** The invoice number uses `random.randint` (`app/billing/service.py`). Use `secrets` if numbers must be hard to guess.
- **11.** The local media `PUT` reads the whole body before checking its size. Dev only.
- **12. Dependencies.** Python versions use `>=` with no lock file, and `pip-audit` is not installed, so they are unscanned. `tools/deploy` has npm advisories (`@fastify/busboy` high, `ajv` moderate) in the Vercel CLI, which runs only in CI. The portal has 0 production vulnerabilities.
- **13. Android.** `allowBackup` is not set, so it defaults to true. A release build with no keystore falls back to the debug signing key instead of failing.
- **14.** Registering a device token for push moves it to whoever sends it. Needs the victim's token, so the risk is low.

## Planned security testing (nothing at the Security Test stage yet)

- A test that tries every route (267 today) as the wrong role and the wrong owner, so a new route without a role check is caught.
- Rate-limit tests, once the limits exist.
- A crew privacy test: crew responses never carry a customer name or mobile number.
- Token storage checks on the mobile app. Cookie, CSRF and session tests for the portal exist in `tests/webauth`.
- The AWS network review (N1 to N13 in `docs/architecture.md`) and the pre-launch security review procedure there.
- V2 (decided for later): two-factor sign-in for admins, and an IP allowlist or WAF in front of the portal.
