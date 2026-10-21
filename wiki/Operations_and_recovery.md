# Operations and recovery

**Operations and recovery** describe how Priveo handles work that cannot proceed as originally scheduled. Missed jobs, customer skips, operational skips and unavailable crew have different outcomes and must remain distinguishable.[^1][^2]

## Could not complete

Crew report Could not complete with a required reason from the administrator-managed list. A note and photo are optional. The affected job becomes Missed; other jobs in the visit are not automatically changed. Administrators receive an alert and choose the outcome.[^1]

Customer service details expose the reason, note and photo. The customer sees a Missed outcome followed by a covered/rescheduled date where applicable. The crew requirements specify no customer push merely for recording the missed outcome.[^1]

## Recovery by service

| Service | Documented missed-job treatment |
|---|---|
| Cleaning-External | Normally covered by the next day's regular job; administrator can instead skip by operations |
| Cleaning-Internal | Retry on the next day only, or skip by operations |
| Deep Spa | Retry on the next day only, or skip by operations |

The next-day restriction is explicit for internal and Spa retries. It does not authorize arbitrary automatic date substitution. Any separate rebooking outside that missed-job flow is handled administratively.[^1][^2]

## Operational skips

Skipping exterior service by operations extends the plan by one day for the affected day. Skipping interior service does not extend the plan or make up that week's interior entitlement. Skipping an add-on does not extend the subscription; refunds or further rebooking are handled outside the automated MVP refund flow.[^2][^3]

A Manager's permitted skip is an operational skip and has the same extension consequences. A customer skip removes service without moving renewal. These actions should not be collapsed into a single undifferentiated “skipped” transaction.[^1][^3]

## Workforce disruption

Exceptions, deactivation and effective society moves can release open assignments. Started or completed history is preserved according to the relevant operation. Unassigned work can be automatically placed where eligible spare capacity exists; otherwise it appears in Needs scheduling.[^2][^4]

Removing work from a frozen schedule needs no unfreeze code. Manual additions or moves normally require it, except for permitted Manager reassignment. Managers can reassign within their society to working Members or Managers; both sides and paired Trainees follow the recorded reassignment behavior.[^1][^2]

## Administrative record

Administrative outcomes, schedule changes and payment/support changes record who acted and when. Audit records support explanation of why a customer lost, gained or moved service. The portal Audit page itself uses explicit refresh rather than promising a live stream.[^2]

## See also

- [Scheduling and capacity](Scheduling_and_capacity.md)
- [Skips and pauses](Skips_and_pauses.md)
- [Workforce management](Workforce_management.md)

## References

[^1]: [Crew requirements](../docs/reqs/crew-functional-requirements.md), CRW-CNC and CRW-MGR.
[^2]: [Admin requirements](../docs/reqs/admin-functional-requirements.md), ADM-CNC, ADM-OPS, ADM-SCH-26–29 and ADM-SET-06.
[^3]: [Customer requirements](../docs/reqs/customer-app-functional-requirements.md), business rules 25–27.
[^4]: [Visit operations](../services/api/app/visits/operations.py); [society moves](../services/api/app/crew/society_moves.py).

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
