# Analytics and privacy

**Analytics and privacy** cover Priveo usage events, session replay, user controls and the handling of personal information in operational and third-party systems. The latest recorded owner decisions select PostHog Cloud in the EU for mobile and portal analytics.[^1]

## Product events

The mobile adapter supports events, screen views, user identification by ID/role and error capture. The portal adapter disables autocapture and uses explicit events plus history-based page views. Its event-cleaning function removes listed personal-property names and scrubs query strings, fragments and record IDs from relevant URL properties.[^2][^3]

Those event filters do not mean all captured content is anonymized. Session replay is a different data path, and application/error content still needs its own review. The implementation should be checked rather than treating a naming convention as an end-to-end privacy guarantee.[^2][^3]

## Session replay decisions

Release replay is off by default through `POSTHOG_REPLAY=false`. The 19 October decisions say replay in enabled test builds covers every mobile role and sign-in screens. Current test recordings mask no text, images, ordinary inputs or touches; password fields remain hidden, and request/response bodies are not recorded under the documented policy.[^1]

The decision record explicitly acknowledges that recordings can contain names, contact numbers, addresses, registration numbers, photographs and payment details stored in the EU. Masking policy and the question of handling customer data outside India remain unresolved before enabling replay for real customers.[^1]

The same day's later decisions supersede any assumption that general masking has already been checked and approved for production.[^1]

## Notice and control

Customer requirements add a plain-language usage-data notice on the email screen and a Settings switch. The notice explains recording of app usage, including screen content, and provides no extra checkbox. These rows are marked Derived.[^4]

Whether tracking needs prior opt-in instead of the present notice/opt-out approach is undecided. Whether administrators need a separate switch is also undecided. The wiki records these as open product decisions and makes no legal-compliance claim.[^1]

## Operational privacy

Crew must not see customer names or mobile numbers. Import reports avoid printing personal identifiers, and real customer spreadsheets stay outside version control. The security backlog separately identifies public permanent media URLs as a high-severity issue requiring private delivery.[^5][^6]

AWS Mumbai is the selected application-hosting direction, but that does not make EU analytics India-resident. The proposed Mani Bond solution has a separate India-only processing boundary and calls for disabling replay in its interface; that proposal must not be silently treated as the policy already implemented for the whole product.[^1][^7]

## See also

- [Security](Security.md)
- [Deployment and hosting](Deployment_and_hosting.md)
- [Mani Bond](Mani_Bond.md)

## References

[^1]: [Owner decisions, 19 October](../docs/reqs/owner-decisions-2026-10-19.md), analytics, replay, hosting and open questions.
[^2]: [Mobile PostHog adapter](../apps/mobile/lib/core/analytics/posthog_analytics.dart).
[^3]: [Portal analytics adapter](../apps/web/src/analytics/analytics.ts).
[^4]: [Customer requirements](../docs/reqs/customer-app-functional-requirements.md), AUTH-18 and SET-05.
[^5]: [Crew requirements](../docs/reqs/crew-functional-requirements.md), CRW-SCH-13; [import command](../services/api/scripts/import_customers.py).
[^6]: [Security backlog](../docs/security-backlog.md), media finding.
[^7]: [Mani Bond architecture](../docs/agent/agent-architecure.md), India boundary and acceptance defaults.

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
