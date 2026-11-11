# Security review of the admin portal and its API, 10 Nov 2026

Scope: the React portal (`apps/web`), every API route the portal uses, the shared sign-in and session code, media, Mani Bond, the cron endpoints, and the deploy workflows. The review was a code read plus `npm audit`, a route walk (all 344 routes) and a repo scan. Nothing was run against test or prod, and nothing was exploited. It replaces the open items of `docs/security-backlog.md` (18 Oct 2026) as the current picture; that file stays as history.

Method note: severity is for a small service with one admin, Indian customers' personal data and no regulator-grade controls yet. "Confirmed" means seen in the code. "Depends" means it turns on a setting that is not in the repo (Vercel, GitHub variables), so check it there.

## What was checked and is sound

- **Every route has an auth rule.** Of 344 routes, 325 require a role (222 admin, 70 customer, 33 crew). The 19 without one are meant to be public or use their own credential: health, config, support contact, legal links, the sign-in and code routes, `/portal`, the signed media links, and the cron route (Bearer `CRON_SECRET`, constant-time compare, refused when unset). No admin route is missing `require_role("admin")`.
- **Sessions.** The cookie is `httpOnly`, `Secure`, `SameSite=Strict`. A CSRF header is required on every cookie-authenticated change, and its value is an HMAC of the session. The server session ends after 60 idle minutes and can be ended from the server. Tokens are checked against a live session on every call, so deactivating a login takes effect at once.
- **Passwords** use Argon2 with a dummy hash for unknown logins. Startup refuses a missing or placeholder `TOKEN_SECRET`, and refuses dev-only settings in prod.
- **Injection.** No raw SQL built from input, no `eval`/`exec`/`pickle`/`shell=True`, no `dangerouslySetInnerHTML` or `innerHTML` in the portal. Emails escape their text. The portal file server blocks path traversal. The spreadsheet loaders are command-line scripts, not endpoints. The weekly CSV export holds only numbers, so there is no formula injection.
- **Secrets.** `.env*` is ignored and not tracked. No keys, keystores or service-account files are in git. Workflows use read-only `contents` permission and no `pull_request_target`.
- **Portal dependencies.** `npm audit --omit=dev`: 0 vulnerabilities.

## Findings

| ID | Severity | Area | Finding | Where | Fix |
|---|---|---|---|---|---|
| R-01 | **High** (agreed fix below) | Admin sign-in | **Anyone can lock the admin out, repeatedly.** The admin ID is fixed and known to everyone with repo access (the current ID, in 89 places across 52 tracked files). Five wrong passwords block it for 15 minutes, the next round for 1 hour, then 24 hours, and the count looks back 24 hours. An attacker who tries again each time a block ends keeps the admin out permanently. Backlog finding 1 fixed *permanent* locks but made this *timed* lock an open denial of service. There is no way for the admin to unlock themselves; only a seed run lifts it (`identity/seed.py`). | `identity/service.py` `login`, `_block_length`; `webauth/router.py` | Count failures per IP + account, not account alone; never block the admin for a correct password from a known device; add a second admin or a break-glass unlock (the seed run) that is documented; add the IP rate limit (R-03). |
| R-02 | **Low** (was High; owner confirmed 10 Nov 2026) | Media | `BLOB_ACCESS` is set as a Vercel secret on both test and prod, so reads go through signed, expiring links. Two small gaps remain: the code falls back to a **public** store when the variable is missing (a deploy to a new project or a typo would silently expose every photo), and files uploaded before the setting was applied may still sit at public addresses (not checked; owner to confirm the stores were created private). | `media/store.py:208` | Make the code refuse `public` when `ENVIRONMENT=prod`, and fail at startup if a Blob token is set without `BLOB_ACCESS`. Confirm both stores show Access: Private in Vercel Storage. |
| R-03 | **High** | Sign-in | **No limit per IP address** (backlog 4, unchanged). One password can be tried on every crew number, customer numbers can be enumerated (`mobile_not_registered` 404), and the code route can be used to send email to any registered customer. The firewall rule was never added. | `/v1/auth/*`, `/v1/web/login` | Vercel Firewall rate rule (30 per IP per 15 min) or an API-side counter table. Needs a plan that allows it. |
| R-04 | **Medium** | Customer sign-in | **A new customer's MPIN is the last 6 digits of their mobile number**, and a customer with the default MPIN is signed in by anyone who knows the number, until the real owner first signs in. The attacker can then set their own MPIN (`must_change_mpin`), take the account, and see addresses, vehicles, payments and photos. Also, a customer's 6-digit MPIN has only 1 million values. | `identity/mpin.py`, `customers/logins.py` | Send the first MPIN by email/WhatsApp as a random value, or require the email code at first sign-in. Expire an unused default MPIN. |
| R-05 | **Medium** | Portal | **No security headers** (backlog 6, unchanged): no Content-Security-Policy, no `frame-ancestors`/`X-Frame-Options`, no `X-Content-Type-Options`, `Referrer-Policy` or HSTS from the API or the portal route. The portal can be framed (clickjacking on a page with destructive actions) and there is no CSP backstop for any future XSS. | `main.py`, `webauth/portal.py`, `vercel.json` | One middleware or `vercel.json` `headers` block: CSP (self + PostHog host + blob host), `frame-ancestors 'none'`, `nosniff`, `Referrer-Policy: same-origin`, HSTS. |
| R-06 | **Medium** | Privacy | **PostHog session replay can record customer data from the admin portal.** When `POSTHOG_REPLAY=true`, nothing is masked except password fields (`maskAllInputs: false`, `mask_all_text: false`), so every customer name, mobile, address and payment shown leaves for a third party. Events are scrubbed, recordings are not. Off by default. *Depends:* check the GitHub variable `POSTHOG_REPLAY` for `test` and `production`. | `apps/web/src/analytics/analytics.ts` | Keep replay off, or mask all text and inputs and block the customer and payment pages before enabling. |
| R-07 | **Medium** | Sessions | **Customer and crew sessions never expire, and refresh-token reuse is not detected** (backlog 7, unchanged). A stolen refresh token works for ever; a second use of an old token just fails with no alarm and no kill of the session family. Admin sessions are fine (idle limits). | `identity/service.py` `refresh`, `_live` | Idle and absolute lifetime for mobile sessions; on reuse of a rotated token end the session. Owner decision on the lifetime. |
| R-08 | **Medium** | Admin model | **One shared admin account with full power and no per-action roles.** Every admin sees and can do everything (reset MPIN, reset crew passwords, change settings, toggle features, record payments, run the scheduler). Actions go to an audit log in only some areas (11 `DirectoryAudit` writes; crew actions are logged), so who did a payment or schedule change is not always traceable. | `platform/deps.py`, whole admin API | Before more than one person has admin: named accounts, a role split (finance, operations, support), and audit coverage for every change. Two-factor is already a decided V2 item; raise its priority. |
| R-09 | **Medium** | Crew | **Crew passwords are guessable** (backlog 5, unchanged): 3 letters of the name, 4 digits and `$`, so about 10,000 options per crew member, and crew cannot change it. Combined with R-03 this is an open brute-force path to crew accounts and the data they can see. | `crew/service.py` `generate_password` | Longer random password, or let crew change it (owner decision CRW-ACC-06). |
| R-10 | **Medium** | Mani Bond | **Business data goes to a third-party model.** Tool results are scrubbed of secrets, emails, customer mobiles and addresses, but customer names, society names, crew names and crew mobiles are kept on purpose, and go to whichever route is configured (OpenRouter, Google, Bedrock). Access is limited to one bound founder login and the tools are read-only (nothing executes an action yet), which is good. Prompt injection from ingested text (docs, complaint text, notes) cannot trigger a write today; it would become serious when action execution is added. *Depends:* which provider is live. | `mani/scrub.py`, `mani/llm.py`, `mani/access.py` | Record the data-sharing decision; use an India-region or no-retention route for personal data; add a human-approval gate and an injection test before any action is executed. |
| R-11 | **Low** | Customer sign-in | **Account enumeration.** `/auth/code` and `/auth/code/verify` answer 404 `mobile_not_registered` for a number that is not a customer (required by AUTH-15). With R-03, this is a free customer list lookup. | `identity/service.py` `_customer` | Rate limit; consider the same answer for unknown numbers (owner decision, because it changes AUTH-15). |
| R-12 | **Low** | Customer account | `change_password`/`change_mpin` does not count wrong current MPINs (backlog 8); an attacker with a stolen session can try all 1,000,000 MPINs with no block. `start_email_change` has no send limit (backlog 9). | `customers/account.py` | Count failures and block like sign-in; cap email-change sends per hour. |
| R-13 | **Low** | Billing | Invoice numbers use `random.randint` (backlog 10). The number is mobile-derived plus 4 random digits, so it is guessable if numbers must be private. | `billing/service.py:673` | `secrets.randbelow`. |
| R-14 | **Low** | Push | Registering a device token moves it to the sender (backlog 14). Needs the victim's token. | `notifications/` | Bind the token to the login that first proves it. |
| R-15 | **Low** | Media (dev store) | Local media `PUT` reads the whole body before the size check (backlog 11). Dev only (`LocalObjectStore`); the Blob store caps size in the client token. | `media/router.py` `put_local` | Check `Content-Length` first and stream. |
| R-16 | **Low** | Settings | `payment.upi_qr_url` accepts any `http://` address, so an admin (or a stolen admin session) could point the customer app's payment QR at an attacker's image. Admin-only and visible, but money-related. | `directory/settings_registry.py:246` | Require `https`; log the change in the audit trail with the old and new value. |
| R-17 | **Low** | API | `X-Request-ID` from the caller is echoed unchanged into logs and the response; a long or forged value can confuse log search. | `platform/middleware.py` | Accept only a short `[A-Za-z0-9-]` value, else generate one. |
| R-18 | **Low** | Test tooling | `DELETE /v1/admin/test-users/{id}` deletes a login and every row below it. It is blocked outside `ENVIRONMENT=test` and limited to the `9000099xxx` range, but it is a mass-delete route compiled into prod, and the 404 hides it. | `testing/smoke_cleanup.py` | Register the router only when `ENVIRONMENT=test`. |
| R-19 | **Low** | Dependencies | Python versions use `>=` with no lock file and `pip-audit` is not installed (backlog 12), so the API's dependencies are unscanned. The portal's dev tooling has 14 advisories (4 high: `undici`, `zod`, `playwright`, in `jsdom`/`eslint`/Playwright), none shipped to the browser. | `services/api/pyproject.toml`, `apps/web` | Pin and lock Python dependencies, run `pip-audit` in CI, run `npm audit fix` for the dev tools. |
| R-20 | **Low** | Android | `allowBackup` is not set (defaults to true), and a release build with no keystore falls back to the debug signing key (backlog 13). Not the portal, but it ships with the same login. | `apps/mobile/android/app/build.gradle.kts:63` | Set `allowBackup=false`; fail the release build without a keystore. |
| R-21 | **Info** | Deploy | The deploy workflow passes `inputs.environment` into shell text and uses `ADMIN_PASSWORD` from the environment secret on every deploy; only repo writers can start it. Third-party actions are pinned to major versions (`@v4`), not commit hashes. | `.github/workflows/*.yml` | Pin actions to SHAs. Keep the production reviewer rule (prod env has none today, per memory notes). |

## Counts

High 2 · Medium 7 · Low 11 · Info 1. Nothing found that gives an unauthenticated visitor admin access or data without first guessing a password or a code. The most urgent two are R-01 (admin lockout) and R-03 (no IP limit), because R-03 also makes R-04, R-09 and R-11 easier.

## Status of the 18 Oct backlog

| Old # | Now |
|---|---|
| 1, 2 | Fixed (but see R-01 for the side effect of fix 1) |
| 3 Media public | Open, R-02 |
| 4 IP limit | Open, R-03 |
| 5 Crew passwords | Open, R-09 |
| 6 Headers | Open, R-05 |
| 7 Session lifetime | Open, R-07 |
| 8, 9, 10, 11, 14 | Open, R-12 to R-15 |
| 12, 13 | Open, R-19, R-20 |

## Not covered

Live testing of test or prod (headers, firewall, `BLOB_ACCESS`, replay variable), the mobile apps beyond Android build settings, Vercel/Supabase account settings (database network access, row security, backups), the PostgreSQL role the API uses (should not be an owner), and a per-route wrong-role/wrong-owner test (planned in the old backlog). The last one would catch a future route without a role check and is worth building.

## Agreed fixes

### R-01 part 1: the admin ID leaves the repo (agreed 10 Nov 2026, owner)

Decision: the admin ID moves to environment configuration and changes to a new value. It is not committed. This hides the ID; it does not stop the lockout. Part 2 (below, not yet agreed) does that.

**What the code change does (done by Claude, one pull request):**

1. New setting `ADMIN_LOGIN_ID`, no default, in `app/platform/config.py`. `check_startup` refuses to start in prod without it and warns on test.
2. `app/identity/seed.py`: reads it from settings. With no value the admin is not seeded and the seed says so. If a login with the old ID exists, the seed renames that same row to the new ID (keeps its password, sessions and audit history) instead of creating a second admin.
3. `app/mani/config.py`: `founder_login_id` defaults to the same `ADMIN_LOGIN_ID` (no default text). Empty still means Mani is off.
4. `app/mani/scrub.py`: reads the ID from settings so the scrubber still redacts it, and also redacts the old ID.
5. `scripts/smoke_test.py`, `test_data.py`, `seed_shared_test_data.py`, `sync_prod_to_test.py`: read `ADMIN_LOGIN_ID` from the environment.
6. About 40 test files (API, web, mobile): use one test constant (`TEST_ADMIN_ID` in the shared fixtures, a `--dart-define` or fixed fake in the Flutter tests) instead of the literal.
7. Docs (11 files), `.env.example` and the test-data skill: say "the admin ID (`ADMIN_LOGIN_ID`)" with no value.
8. A test fails the build if the old ID reappears in a tracked file, so it cannot creep back.
9. Workflows (`api-deploy-vercel.yml`, `mobile-integration.yml`): pass `vars.ADMIN_LOGIN_ID` to the seed, smoke and integration steps.

**What the owner does, in this order (the order matters):**

1. Choose the new ID. Use something not guessable from the business name, 12 characters or more, letters and digits, for example a random word pair plus digits. Keep it out of chat, email and screenshots.
2. Add `ADMIN_LOGIN_ID=<new id>` to `services/api/.env` (already git-ignored).
3. Add it as a **variable** (not a secret is fine, but a secret is better) in the GitHub Environments `test` and `production`.
4. Add `ADMIN_LOGIN_ID` to the Vercel projects `priveo-api-test` and `priveo-api-prod` (Production scope).
5. Tell Claude when 2 to 4 are done. Only then is the pull request merged. Test deploys first and the seed renames the admin row there. Check you can sign in to the portal on test with the new ID and the same password.
6. Release to prod with a `v*` tag as usual. The same rename happens there. Sign in once and confirm.
7. After that, the old ID is only in git history. Tell the portal users (you and anyone else) the new ID.

**Rollback:** set `ADMIN_LOGIN_ID` back to the old value and re-run the seed; the row is renamed back.

**Order warning:** if the code is deployed before the variable exists, prod refuses to start (by design) and test skips the admin seed. This is why step 5 waits.

### R-01 part 2: the lockout itself (proposed, not yet agreed)

Count wrong passwords by IP address plus ID instead of by ID alone, never lock a correct password out for a known device, and add the IP limit of R-03. This needs the owner's decision on how a locked admin is let back in.

### R-05: security headers (added to the fix plan 10 Nov 2026; backlog B-20)

Status: built 10 Nov 2026 (pull request on branch `fix/r05-security-headers`). The CSP ships in report-only mode, controlled by the setting `CSP_MODE` (`report-only` default, `enforce`, `off`), so the merge changes no behaviour in the browser except the four always-on headers. Differences from the plan: `img-src` allows any `https:` host (photos come from the media store, public or signed); no `/docs` handling because the API serves no `/docs` or `/redoc`. Next: walk the portal on test with the console open, then set `CSP_MODE=enforce` on test, then prod (a Vercel variable, no code change).

**What the code change does (one pull request, no migration):**

1. One middleware in `app/main.py` (next to `RequestIdMiddleware`) adds the headers to every API and portal response, so the portal files served by `webauth/portal.py` are covered too. `vercel.json` is not needed.
2. Headers:
   - `Content-Security-Policy`: `default-src 'self'`; `script-src 'self'`; `connect-src 'self'` plus the PostHog host (`https://eu.i.posthog.com`, `https://eu.posthog.com`, from `apps/web/src/analytics/analytics.ts`); `img-src 'self' data: blob:` plus the Blob store host; `style-src 'self' 'unsafe-inline'` (shadcn/Tailwind inline styles, check); `frame-ancestors 'none'`; `base-uri 'self'`; `form-action 'self'`; `object-src 'none'`.
   - `X-Frame-Options: DENY` (older browsers), `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`.
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (no `preload`).
3. The API's `/docs` and `/redoc` pages load scripts from a CDN, so they get a looser policy or none (check which are enabled in prod).
4. Tests: a response from `/v1/public/config` and from `/portal/` carries each header; the portal index loads with no CSP violation in the Playwright run (fail on console CSP errors).

**Rollout (the order matters):**

1. Ship the CSP as `Content-Security-Policy-Report-Only` on test first, open the portal, walk the main pages (board, customers, payments, photos, PostHog on), and read the browser console for violations.
2. Fix the allow-list, then switch to enforcing `Content-Security-Policy` on test, then prod with a `v*` tag.
3. The owner checks the portal on test after step 2.

**Open for the owner:** whether session replay (R-06) will ever be turned on, because replay needs extra PostHog hosts and `worker-src blob:` in the policy.

**Rollback:** remove the middleware, or set the CSP back to report-only. The other headers are harmless to keep.

### R-07: customer and crew sessions (added to the fix plan 10 Nov 2026; backlog B-24)

Status: Part 1 built 10 Nov 2026 (pull request on branch `fix/r07-refresh-reuse`, migration 0058). Part 2 changes an owner rule and waits for the owner.

**What the code does today (`identity/service.py`):** `refresh` looks up the session by the hash of the presented token, swaps in a new token and returns. `_live` ends a session by idle time only for web sessions and for admin sessions on the phone. A customer or crew session on the phone has no idle limit and no absolute limit. The session row keeps only the current hash, so a token that was already used is indistinguishable from a made-up one: it fails with 401 and nothing else happens.

**Part 1: detect reuse of a rotated token (no owner decision needed, does not change AUTH-17 or CRW-ACC-11)**

1. Migration (next number after 0057, written by hand): `auth_sessions.previous_refresh_hash` (String(64), nullable, indexed) and `auth_sessions.rotated_at` (nullable).
2. `refresh`: before swapping, copy the current hash to `previous_refresh_hash` and set `rotated_at`.
3. When the presented token matches no current hash, look for a session whose `previous_refresh_hash` matches. Then:
   - If `rotated_at` is within a grace window (proposed 2 minutes), answer 401 and change nothing. This is the honest case: the phone sent the refresh, lost the reply and retried with the old token.
   - Otherwise it is reuse. End that session (`ended_reason="token_reuse"`), write an `AuthEvent` of kind `refresh_reuse`, and answer 401. The real owner is signed out and signs in again with the MPIN or password; the thief's token is dead too.
4. The grace window is the one judgment call. Too short signs real users out on bad networks. Too long gives a thief a window. Start at 2 minutes and read the `refresh_reuse` events on test before prod.
5. The admin sessions list (ADM-CUS-21, ADM-CRW-21) shows "Signed out: token reuse" for these sessions. No new screen.
6. Tests (SQLite and PostgreSQL): normal refresh chain still works; old token inside the window gives 401 and leaves the session alive; old token after the window ends the session and logs the event; the new token is dead after a reuse; a different session's tokens are not touched; two concurrent refreshes with the same token end with one winner (row lock or a unique update, check on PostgreSQL).
7. The app: on 401 from refresh it already goes to the sign-in screen. Confirm that, and that a retry after a lost reply does not loop.

**Part 2: a lifetime for mobile sessions (needs the owner; changes the rule)**

AUTH-17 and CRW-ACC-11 are marked Owner: the app stays signed in with no time-out until logout, MPIN change or reset, admin sign-out, a new phone or deactivation. A lifetime is therefore a decision, not a fix. Options to put to the owner:

| Option | What changes | Cost to the user |
|---|---|---|
| A. Keep as is | Nothing. Part 1 plus the existing admin sign-out are the controls. | None. The risk of a stolen token staying valid remains until the owner signs it out. |
| B. Absolute lifetime of 90 days from sign-in (recommended if any limit is wanted) | `_live` ends a mobile session older than 90 days with reason `expired`. | A customer or crew member signs in again every 3 months with MPIN or password. |
| C. Idle limit of 30 days | `_live` ends a mobile session unused for 30 days. | Only people who stop using the app are signed out; active users never notice. |
| D. B and C together | Both rules. | Same as B for the long run. |

If the owner picks B, C or D: the limits go in settings (not hard-coded), AUTH-17 and CRW-ACC-11 are reworded and the version lines bumped, the three requirement files stay consistent, and tests cover the edge of each limit. The crew app's field use (a phone on a site every day) means C costs crew nothing; B costs them a re-sign-in, so the owner may want crew and customers on different values.

**Rollout:** Part 1 on test first (merge deploys to test), watch `refresh_reuse` events for a few days, then a `v*` release to prod. Part 2 follows only after the owner's choice.

**Rollback:** Part 1 is additive. Remove the check in `refresh` and the new columns are unused.
