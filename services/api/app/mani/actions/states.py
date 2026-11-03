"""The one table of allowed proposal state changes (architecture 6.6).

draft -> awaiting_approval -> approved -> executing -> succeeded or failed, plus rejected,
cancelled, expired and invalidated. Every other move is refused."""
from datetime import timedelta

DRAFT = "draft"
AWAITING_APPROVAL = "awaiting_approval"
APPROVED = "approved"
EXECUTING = "executing"
SUCCEEDED = "succeeded"
FAILED = "failed"
REJECTED = "rejected"
CANCELLED = "cancelled"
EXPIRED = "expired"
INVALIDATED = "invalidated"

STATES = (DRAFT, AWAITING_APPROVAL, APPROVED, EXECUTING, SUCCEEDED, FAILED,
          REJECTED, CANCELLED, EXPIRED, INVALIDATED)

TRANSITIONS: dict[str, frozenset[str]] = {
    DRAFT: frozenset({AWAITING_APPROVAL, CANCELLED, EXPIRED}),
    AWAITING_APPROVAL: frozenset({APPROVED, REJECTED, CANCELLED, EXPIRED, INVALIDATED}),
    APPROVED: frozenset({EXECUTING, CANCELLED, EXPIRED, INVALIDATED}),
    EXECUTING: frozenset({SUCCEEDED, FAILED}),
    SUCCEEDED: frozenset(),
    FAILED: frozenset(),
    REJECTED: frozenset(),
    CANCELLED: frozenset(),
    EXPIRED: frozenset(),
    INVALIDATED: frozenset(),
}

TERMINAL = frozenset(state for state, nxt in TRANSITIONS.items() if not nxt)
# States that can still time out: an approval is only good for five minutes.
EXPIRABLE = frozenset({DRAFT, AWAITING_APPROVAL, APPROVED})
# Moving into these needs a live (unexpired) proposal.
NEEDS_LIVE = frozenset({APPROVED, EXECUTING})

APPROVAL_WINDOW = timedelta(minutes=5)
