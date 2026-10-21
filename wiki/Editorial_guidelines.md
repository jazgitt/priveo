# Editorial guidelines

These **editorial guidelines** define the structure, evidence standards and maintenance rules for the Priveo wiki. The wiki adapts encyclopedic layout, neutral description and verifiability to a repository knowledge base. It is not an article submission to Wikipedia.[^1][^2][^3]

## Article structure

Each article uses one descriptive title, an opening definition or summary, logically ordered sections, relevant cross-links and a References section. Headings use sentence case. A compact infobox or comparison table is useful where the information is genuinely parallel. Longer topics should summarize and link to focused articles rather than grow indefinitely.[^1]

The main page groups the full article inventory. Each article links back to it and identifies the evidence-review date. This navigation and date convention is local wiki policy.

## Length and scope

Every Markdown article must stay at or below **2,000 words**. This limit includes headings, tables, navigation and reference text. The validator conservatively counts whitespace-separated words in the complete Markdown source, including link targets; it may therefore count more than a rendered prose count.

Split an overlong article by subject and keep a concise overview with links. Avoid duplicate descriptions of the same rule across many pages. Workflow articles may explain a process, but should not become dumps of every requirement row or entire source files.

## Neutrality and precision

Describe what the product does, what the requirements specify and what evidence establishes. Avoid marketing claims, invented customer counts, unsupported availability/performance promises and claims of production or legal readiness.[^2]

Use explicit evidence language:

| Wording | Appropriate evidence |
|---|---|
| “The requirements specify” | Identified requirement or owner decision |
| “The implementation contains” | Relevant current source |
| “The report records” | Dated verification record |
| “The plan proposes” | Design or roadmap proposal |
| “Deployed” | Actual environment/deployment evidence |

A requirement is not a passing test. Source presence is not deployment. High line coverage is not complete branch coverage, security assurance or acceptance coverage.[^4]

## Citations

Use numbered Markdown footnotes near the supported paragraph or table. References link directly to repository documents/code, with requirement IDs or section names where helpful. Link local sources relatively so the wiki remains browsable in the checkout and on repository hosts. External references use descriptive link text.[^3]

The project is documented primarily from its own sources. This is suitable for an internal knowledge base but does not establish the independent reliable sourcing or public notability needed for a Wikipedia article. Do not imply independent validation by citing one project document through another.

For changing facts, identify the review or measurement date. Attribute historical test counts and estimates to their reports. Avoid treating current provider pricing or availability as verified merely because a repository proposal mentions them.

## Resolving conflicts

Owner decisions supersede older prototype behavior. Current requirement rows can supersede stale summaries elsewhere in the same file. For implementation claims, inspect the actual code. Prefer newer measured reports for test outcomes, while retaining their exclusions.[^4][^5]

If sources still disagree, state the conflict and link both; do not silently invent a resolution. Examples documented in this wiki include crew society transfers, RC handling and visit-completion wording. Real environment migration state requires inspection of that environment.

## Maintenance and validation

Run `python wiki/validate.py` from the repository root after changes. It checks article length, title/section structure, local links and Markdown anchors, footnote completeness, main-page coverage and reachability. External destinations and factual truth require editorial review; the script does not fetch websites or inspect live environments.

When product rules change, update the relevant article and nearby cross-links, confirm source references and revise the evidence date for articles actually reviewed. Keep credentials, customer records and private operational exports out of the wiki.

## See also

- [Requirements and roadmap](Requirements_and_roadmap.md)
- [Testing](Testing.md)

## References

[^1]: [Wikipedia Manual of Style: Layout](https://en.wikipedia.org/wiki/Wikipedia:Manual_of_Style/Layout), consulted 20 October 2026; adapted article organization.
[^2]: [Wikipedia: Neutral point of view](https://en.wikipedia.org/wiki/Wikipedia:Neutral_point_of_view), consulted 20 October 2026; neutral description.
[^3]: [Wikipedia: Verifiability](https://en.wikipedia.org/wiki/Wikipedia:Verifiability), consulted 20 October 2026; traceable sourcing.
[^4]: [Test report, 20 October](../docs/testing/test-report-2026-10-20.md); [static requirements audit](../docs/coverage/requirements-audit.md).
[^5]: [Repository conventions](../CLAUDE.md), owner decisions, prototype precedence and stable IDs.

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
