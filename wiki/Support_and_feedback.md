# Support and feedback

**Support and feedback** collect customer service problems, visit ratings, general feedback and cycle-based check-ins. These are distinct records with different purposes and validation rules.[^1]

## Help and complaints

Support offers FAQ, Report an issue, My complaints and Give feedback, plus telephone and WhatsApp links. The FAQ is app-bundled Markdown, so changing that content requires a new app version. The displayed support hours come from support configuration; the starting requirement shows 6 AM–10 PM.[^1][^2]

An issue requires a category and description, with optional photographs and a linked visit. The visit defaults from the initiating context or selected vehicle's latest visit; “No linked visit” is allowed. Starting categories include cleaning quality, missed service, damage concern, crew behaviour, billing and other.[^1]

Complaints receive identifiers in the `#C-NNNN` format. Their states are Raised, In progress and Resolved. Administrators can update status and add notes visible to the customer, recording who acted and when.[^1][^3]

## Response target

The customer confirmation promises a response as soon as possible without a fixed response time. The internal target is a reply within four hours. Complaints still Raised after that interval are highlighted and escalated under the administrator rules. This internal target must not be rewritten as a customer-facing four-hour guarantee.[^1][^3]

## Visit ratings

A visit can receive a one-to-five-star general rating, associated tags and comments. Ratings are not assigned to individual crew members, and the crew app does not expose them. Positive tags and lower-rating issue categories come from administrator-managed data.[^1][^4]

## General feedback

After onboarding, a movable edge icon opens the feedback modal; Support offers another entry. Feedback includes category, stars and comments. At least a rating or comment is required; category alone is insufficient.[^1]

Testimonial permission is a separate checkbox, off by default. Priveo may quote the customer's feedback only when that permission is supplied. This permission is unrelated to notification preferences or analytics choices.[^1]

## Monthly check-in

Four days before renewal by default, the customer is invited to rate administrator-managed categories for that vehicle's subscription cycle. Categories include recommendation, value, schedule fit, crew professionalism, app/support and interest in add-ons.[^1]

At least one category needs a rating; a general comment is optional. Answers are associated with the subscription and renewal cycle. The Home card remains until completion even if the customer disabled the check-in notification. Older results retain original category names after reference-data edits.[^1][^5]

## See also

- [Notifications](Notifications.md)
- [Calendar and history](Calendar_and_history.md)
- [Site setup](Site_setup.md)

## References

[^1]: [Customer requirements](../docs/reqs/customer-app-functional-requirements.md), SUP, ISS, CMP, SVC, FDBK and CHK.
[^2]: [FAQ asset](../apps/mobile/assets/content/faq.md).
[^3]: [Admin requirements](../docs/reqs/admin-functional-requirements.md), ADM-CMP and ADM-FDB.
[^4]: [Crew requirements](../docs/reqs/crew-functional-requirements.md), CRW-RAT-01.
[^5]: [Owner decisions, 13 October](../docs/reqs/owner-decisions-2026-10-13.md), historical category names.

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
