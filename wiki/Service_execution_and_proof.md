# Service execution and proof

**Service execution and proof** link a Priveo job to recorded work, timed checklist completion and uploaded media. The customer receives evidence of the service rather than only a completed status.[^1][^2]

## Jobs and visits

A job represents a particular service assigned to crew. A regular visit may contain exterior and interior jobs. Those jobs may be assigned separately. A separately purchased add-on is independent of the day's regular visit and must not block that visit's completion.[^1][^2]

The customer business rules define a visit as complete when all its jobs are done or skipped. Some crew wording describes completion in terms of all jobs being Completed; the cross-role distinction should be checked when changing completion code. Neither wording allows unuploaded mandatory proof to count as completed work.[^1][^2]

## Checklists

Administrators maintain ordered service-specific checklists and proof minimums. Crew can check items but cannot rename, add or remove them. Each check records its time. Customers inspect those checks and timestamps in Service Details.[^1][^3]

Issued history retains the original checklist wording even when the catalogue is renamed or deactivated. The owner approved editable five-step samples for interior cleaning and Deep Spa; these are starting content, not an immutable service specification.[^3][^4]

The implementation uses issued checklist snapshots. Legacy or unmigrated jobs without a snapshot have a compatibility fallback to directory labels and recorded item keys; their original labels may be unknown. The historical-preservation requirement should not be read as a claim that missing legacy wording can be reconstructed.[^8]

## Media and completion

Crew may use camera or gallery, labelling media Before, During or After. The requirements accept common Android/iOS camera formats, including HEIC, with photos under 10 MB and videos under 25 MB. RC documents have a separate 5 MB rule.[^1][^2]

“Mark complete” requires all checklist items and the service's configured minimum photo/video counts. The backend saves the finish time and completed state. Customers see the relevant crew, checklist and media; visit ratings remain general rather than assigned to an individual crew member.[^1]

## Upload reliability

An offline upload queue preserves files and retries when connectivity returns. A signed-out crew member's pending files should survive for the next sign-in. Upload ownership and queue restoration therefore matter as much as the visible progress indicator.[^1][^5]

The media layer issues upload tickets, confirms storage and serves readable media URLs through an object-store abstraction. Local development and Vercel Blob behavior are present in the repository. Private S3 delivery remains launch work; the documented Blob read URLs are public and permanent.[^6][^7]

## Corrections and failed service

Crew cannot edit a completed job. Corrections go through administrators. If service cannot be performed, crew select a reason and may supply a note/photo; that evidence belongs to a Missed outcome rather than normal completion proof.[^1]

## See also

- [Calendar and history](Calendar_and_history.md)
- [Operations and recovery](Operations_and_recovery.md)
- [Security](Security.md)

## References

[^1]: [Crew requirements](../docs/reqs/crew-functional-requirements.md), CRW-SVC and CRW-CNC.
[^2]: [Customer requirements](../docs/reqs/customer-app-functional-requirements.md), SVC and business rules 8, 17 and 27.
[^3]: [Admin requirements](../docs/reqs/admin-functional-requirements.md), ADM-CHK.
[^4]: [Owner decisions, 13 October](../docs/reqs/owner-decisions-2026-10-13.md), sample checklists.
[^5]: [Mobile upload queue](../apps/mobile/lib/features/crew/upload/upload_queue.dart).
[^6]: [Media router](../services/api/app/media/router.py); [object stores](../services/api/app/media/store.py).
[^7]: [Security backlog](../docs/security-backlog.md), finding 3.
[^8]: [Issued checklist reader](../services/api/app/visits/checklists.py), snapshot and legacy fallback.

---

[Main page](README.md) | [Glossary](Glossary.md) | [Editorial guidelines](Editorial_guidelines.md)

*Evidence reviewed: 20 October 2026. Requirements, implementation and verification may have different status.*
