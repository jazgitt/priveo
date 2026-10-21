# Identity and access

**Identity and access** determine who can sign in to Priveo, which application experience they receive and which records they may use. Customer, crew and administrator logins share an entry screen but use different identifiers and onboarding rules.[^1][^2]

| Audience | Identifier | Initial access |
|---|---|---|
| Customer | Email | Email verification, password creation, onboarding review |
| Crew | Ten-digit mobile number | Administrator-generated password |
| Administrator | User ID | Seeded or configured administrator credentials |

## Customer verification

Only administrator-created customers can sign in during MVP. Email matching is case insensitive. First sign-in uses an emailed six-digit code valid for 30 minutes. Five wrong attempts cancel the code; the requirements allow at most five code requests per hour and a 30-second resend countdown. A password requires at least eight characters, a letter and a number.[^1]

Returning customers use email and password. Forgot-password and email-change flows also use emailed codes. Contact mobile numbers are not SMS-verified login identities. Terms acceptance is recorded at first sign-in.[^1]

## Crew and administrator access

Crew login IDs are their mobile numbers. Administrators generate and reset crew passwords and see each new password once; only its hash is stored. The documented generated format uses a name prefix, four random digits and a fixed symbol. Crew cannot change their login ID or password themselves.[^2]

Current crew/admin requirements use temporary lockouts after repeated wrong passwords: 15 minutes, then one hour, then 24 hours for repeated blocks within a day. Administrators can unlock a crew login or reset its password. The weak generated-password pattern remains an explicit security finding.[^2][^3]

## Sessions and authorization

Customer and crew mobile sessions are intended to persist until logout, password reset/change, administrative sign-out or deactivation. Administrator web sessions end after 60 minutes of inactivity. Administrators can inspect and terminate relevant customer and crew sessions.[^1][^2][^4]

Mobile API access uses bearer credentials; the portal uses cookie-based sessions with CSRF protection for mutations. Backend authorization must check role and record ownership. Hiding a screen is not sufficient to protect the corresponding endpoint.[^5]

Crew must not receive customer names or mobile numbers. Manager privileges are confined to their society and do not include full administrator functions.[^2]

## Verification limits

The 20 October report records existing login, hash, cookie, CSRF and session tests, but no comprehensive security suite or every-route authorization audit. Persistent mobile sessions and refresh-token reuse remain backlog concerns.[^3][^6]

## See also

- [Security](Security.md)
- [Crew app](Crew_app.md)
- [Admin portal](Admin_portal.md)

## References

[^1]: [Customer requirements](../docs/reqs/customer-app-functional-requirements.md), AUTH and account settings.
[^2]: [Crew requirements](../docs/reqs/crew-functional-requirements.md), CRW-ACC and CRW-MGR.
[^3]: [Security backlog](../docs/security-backlog.md), findings 1, 5 and 7.
[^4]: [Admin requirements](../docs/reqs/admin-functional-requirements.md), ADM-ACC, ADM-CUS-21 and ADM-CRW-21.
[^5]: [Web authentication implementation](../services/api/app/webauth/router.py); [platform dependencies](../services/api/app/platform/deps.py).
[^6]: [Test report, 20 October](../docs/testing/test-report-2026-10-20.md), security tests.

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
