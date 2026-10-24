# Requirements and roadmap

**Requirements and roadmap** describe how Priveo distinguishes agreed behavior, implementation progress, verification and future work. The source base includes three role-specific requirement documents, dated owner decisions, code, audits and test reports.[^1]

## Requirement conventions

Customer IDs use prefixes such as AUTH, ONB, PAY, HOME, CAL, SVC, SKIP, PAUSE, SUB, VEH, ADD, SUP, CMP, FDBK and CHK. Administrator IDs start ADM and crew IDs CRW. IDs remain stable when surrounding rows change; retired gaps are not renumbered.[^1]

The requirements' status column describes provenance: Defined, Stub, Derived, Owner or Open. It does not indicate a test result. A separate feature-stage tracker records delivery progress.[^1][^2]

Owner decisions override conflicting prototype behavior. The customer prototype is historical evidence, not a source for reintroducing AutoPay, SMS OTP, a rest day or included Deep Spa after those choices were changed.[^1]

## Evidence chronology

| Source/checkpoint | What it establishes |
|---|---|
| Architecture/build drafts | Intended design and original delivery phases |
| 13 October owner decisions | Standalone Spa, sample checklists, tax snapshots, optional planning and configurable policies |
| 13 October requirements audit | Static requirement-to-source mapping at that date |
| Later requirement revisions | Added/changed product behavior, including catalogue offerings and dated crew transfers |
| 19 October owner decisions | Hosting and analytics/replay decisions |
| 20 October test/coverage reports | Recorded suite results, stage reconciliation and explicit exclusions |

The static audit's “Implemented” means a source path was located; it is not acceptance or deployment evidence. Its 426-row scope is older than the 461-ID reconciliation in the 20 October report.[^2][^3]

## Recorded stage inventory

The 20 October reconciliation records Draft 88, Backlog 96, In Dev 84, Unit Tested 105, Functional Tested 88 and Security Test 0, totaling 461. New or changed requirements return to Draft. Passing tests mapped by ID support promotion, subject to the report's stated mapping limitations.[^2]

The stage named “Unit Tested >95%” should not be interpreted as a measured 95% line-coverage result for each requirement or role. The actual per-area gate is 90% executable lines.[^2][^4]

## Remaining product and engineering work

Recorded work includes immediate multi-client refresh, complete PDF/proof device flows, live push/email/media integration, private S3, provider configuration, security checks, production hosting and release validation. Optional automatic planning is implemented but disabled by default and still requires operational invocation.[^5]

The 20 October report adds a fuller scenario rerun, review of test-to-requirement mappings, deferred ruff fixes and device/emulator/hosted-database validation. Old handoff statements about unapplied migrations are environment-specific historical checkpoints, not a fresh database inspection.[^2][^5]

## Deferred and proposed scope

Public signup, automated payments, in-app refunds and selected security upgrades are deferred in the role requirements. Some older deferred entries, such as crew society transfer, are superseded by newer requirement rows and implementation. The proposed Mani Bond assistant has separate scope and gates.[^1][^6]

## See also

- [Testing](Testing.md)
- [Mani Bond](Mani_Bond.md)
- [Editorial guidelines](Editorial_guidelines.md)

## References

[^1]: [Project README](../README.md); [customer requirements](../docs/reqs/customer-app-functional-requirements.md); [admin requirements](../docs/reqs/admin-functional-requirements.md); [crew requirements](../docs/reqs/crew-functional-requirements.md).
[^2]: [Test report, 20 October](../docs/testing/test-report-2026-10-20.md), stage reconciliation and limitations; [feature tracker](../docs/feature-status.json).
[^3]: [Requirements audit](../docs/coverage/requirements-audit.md); [owner decisions, 13 October](../docs/reqs/owner-decisions-2026-10-13.md); [owner decisions, 19 October](../docs/reqs/owner-decisions-2026-10-19.md).
[^4]: [Measured coverage](../docs/coverage/unit-test-coverage.md).
[^5]: [Test report, 20 October](../docs/testing/test-report-2026-10-20.md).
[^6]: [Mani Bond solution plan](../docs/agent/mani-bond-solution-plan.md).

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
