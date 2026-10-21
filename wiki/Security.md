# Security

**Security** in Priveo combines authentication and session controls, role/ownership boundaries, configuration checks and a recorded backlog. The reviewed backlog comes from an 18 October 2026 code/dependency/history review; it is not a penetration-test certificate.[^1]

## Existing controls

Passwords are stored as hashes. Mobile credentials and portal sessions use different transport/session mechanisms. Portal mutations have CSRF controls. Administrative sign-out, deactivation and password reset end relevant sessions.[^2][^3]

Two review findings are recorded as fixed: indefinite account locking was replaced by timed blocks, and hosted startup now rejects unsafe secrets/environment configuration. Production rejects development-only settings. The portal also applies its 60-minute idle timeout.[^1]

These controls do not establish that every endpoint enforces correct role and ownership. The planned every-route authorization suite remains separate work.[^4]

## Open findings

| Area | Recorded issue |
|---|---|
| Media | Public permanent Blob read URLs expose sensitive uploaded content |
| Abuse prevention | No complete per-IP sign-in limit |
| Crew credentials | Predictable generated password structure |
| Web hardening | Missing documented security headers |
| Mobile sessions | Persistent refresh sessions without reuse detection |
| Account changes | Gaps in wrong-current-password and email-send limiting |
| Dependencies | Unlocked/unscanned Python packages and deployment-tool advisories |
| Android | Backup default and release debug-signing fallback |
| Push registration | Device token can be reassigned to the registering account |

The backlog also notes random invoice-number generation and local upload body-size handling. Severity and proposed remedies belong to the source record and should be reevaluated after fixes rather than copied indefinitely.[^1]

## Private data

Crew responses must exclude customer names and contact numbers. Media can contain number plates, RC documents, complaint images and service evidence. Private storage with short-lived access is therefore a functional security requirement, not just a hosting optimization.[^1][^3]

Replay in enabled test builds can capture personal content and sends it to PostHog EU. Release replay remains off. The owner has not settled the masking and consent questions needed before real-customer enablement.[^5]

## Scheduled endpoints

Internal jobs require a bearer secret and refuse execution when it is missing. That protects the endpoint but also means automated billing/reminders will not operate if host configuration is absent. Deployment and monitoring must verify both authorization and actual invocation.[^6]

## Validation and release limits

The 20 October report records some auth, hash, cookie, CSRF and session tests inside ordinary suites. It explicitly says no comprehensive security tests exist and the Security Test stage is empty. Planned work includes role/ownership checks across routes, rate limits, crew privacy, mobile token storage and AWS network review.[^4]

This article reports repository findings as of the review date. It does not assert present vulnerability counts from a new scan, regulatory compliance or production approval.

## See also

- [Identity and access](Identity_and_access.md)
- [Analytics and privacy](Analytics_and_privacy.md)
- [Deployment and hosting](Deployment_and_hosting.md)

## References

[^1]: [Security backlog](../docs/security-backlog.md).
[^2]: [Platform configuration](../services/api/app/platform/config.py); [web authentication](../services/api/app/webauth/router.py).
[^3]: [Crew requirements](../docs/reqs/crew-functional-requirements.md), access, privacy and sessions.
[^4]: [Test report, 20 October](../docs/testing/test-report-2026-10-20.md), security testing.
[^5]: [Owner decisions, 19 October](../docs/reqs/owner-decisions-2026-10-19.md).
[^6]: [Cron authorization](../services/api/app/notifications/cron.py).

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
