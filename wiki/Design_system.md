# Design system

Priveo's **design system** combines shared brand assets and tokens with role-specific mobile themes and a web component library. It aims to keep status meanings and product language consistent while adapting screens to customers, crew and administrators.[^1][^2]

## Brand and tokens

The brand folder holds logos and `tokens.json`. Manrope is the body typeface; Cormorant Garamond is used for display text. Gold is the primary action accent and wine a secondary accent. Status colors distinguish completed, scheduled, warning, Spa and error states, accompanied by text labels.[^1]

The tagline is “Own the Car. We'll Handle the Rest.” The documented voice is calm, polite and concise. Dates follow `dd-Mon-yy`, and product prices are expressed in rupees including GST.[^1]

Theme generators produce Flutter and portal outputs from the shared tokens. The runtime theme and components should be consulted when an older design table differs from the current role presentation.[^2]

## Role appearance

Customer, splash and login screens use the dark appearance derived from the prototype. Crew screens use a plain white appearance, and administrator screens use cream. The build guide records these as fixed role looks independent of the phone's light/dark setting, superseding earlier draft proposals for a user-selectable theme.[^3]

Customer screens also retain some prototype corner dimensions that differ from shared token defaults. Those differences are documented implementation choices rather than evidence that all themes are generated without overrides.[^3]

## Portal patterns

The portal uses React, Tailwind and shadcn-style shared components. Shared page blocks support mutation feedback, confirmation for destructive actions and long-running task presentation. Summary tiles and status tabs connect operational counts to filters rather than serving only as decoration.[^4]

The product requirements define the content and behavior of cards and lists: for example, Home uses one combined vehicle card with no plan price, and subscriptions/payments/complaints have specific summaries. Visual similarity to an older prototype does not override those newer decisions.[^5]

## Accessibility and evidence

Design guidance calls for readable contrast, text labels alongside colors, suitable touch targets and resilience to larger text. The feedback edge icon has a screen-reader label even though it has no visible caption. Crew targets are intended to be larger for operational use.[^1][^5]

These are design requirements and guidance, not a completed accessibility certification. Golden and widget tests support visual checks, while real-device testing and Linux golden comparisons remain outside the latest local validation report.[^6]

## See also

- [Customer app](Customer_app.md)
- [Admin portal](Admin_portal.md)
- [Development](Development.md)

## References

[^1]: [Technical stack and brand guide](../docs/tech-stack.md), section 6; [brand tokens](../docs/brand/tokens.json).
[^2]: [Flutter theme](../apps/mobile/lib/core/ui/theme.dart); [mobile theme generator](../apps/mobile/tool/gen_theme.dart); [web theme generator](../apps/web/tools/gen-theme.mjs).
[^3]: [Build guide](../docs/build-and-release.md), role appearance and documented token differences.
[^4]: [Portal UI review](../docs/design/admin-portal-ui-review.md); [web package](../apps/web/package.json).
[^5]: [Customer requirements](../docs/reqs/customer-app-functional-requirements.md), HOME-02 and FDBK-01; [admin requirements](../docs/reqs/admin-functional-requirements.md), list summaries.
[^6]: [Test report, 20 October](../docs/testing/test-report-2026-10-20.md), exclusions.

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
