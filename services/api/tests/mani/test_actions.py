"""Walk WP1: the proposal records, the state table, hash binding, expiry and retention."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.identity.models import Login
from app.mani.actions import service, states
from app.mani.actions.models import ManiApproval, ManiAudit, ManiExecution, ManiProposal
from app.mani.models import ManiConversation, ManiRun
from app.mani.retention import sweep_actions
from app.mani.service import delete_conversation_rows

NOW = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
PARAMS = {"society": "s1", "from": "2026-11-03", "to": "2026-11-09"}


@pytest.fixture
def founder_id(db, client):
    return db.scalars(select(Login.id).where(Login.login_id == "testadminid")).one()


def make(db, founder_id, params=None, now=NOW, **kw):
    return service.create_proposal(
        db, login_id=founder_id, action="run_schedule", params=params or dict(PARAMS),
        preview={"summary": "Plan the week"}, record_versions={"schedules:1": "v1"}, now=now, **kw)


def audit_of(db, proposal):
    return list(db.scalars(select(ManiAudit).where(ManiAudit.proposal_id == proposal.id)
                           .order_by(ManiAudit.created_at, ManiAudit.event)))


# ---- The table ----------------------------------------------------------------------------


def test_every_state_has_a_row_and_only_known_targets():
    assert set(states.TRANSITIONS) == set(states.STATES)
    for targets in states.TRANSITIONS.values():
        assert targets <= set(states.STATES)


def test_finished_states_are_dead_ends():
    assert states.TERMINAL == {states.SUCCEEDED, states.FAILED, states.REJECTED, states.CANCELLED,
                               states.EXPIRED, states.INVALIDATED}
    assert all(not states.TRANSITIONS[s] for s in states.TERMINAL)


@pytest.mark.parametrize("current", states.STATES)
@pytest.mark.parametrize("target", states.STATES)
def test_only_the_listed_moves_are_allowed(db, founder_id, current, target):
    p = make(db, founder_id)
    p.status = current
    allowed = target in states.TRANSITIONS[current]
    if allowed:
        service.transition(db, p, target, actor_id=founder_id, now=NOW)
        assert p.status == target
    else:
        with pytest.raises(service.IllegalTransition):
            service.transition(db, p, target, actor_id=founder_id, now=NOW)
        assert p.status == current


def test_the_happy_path_and_one_audit_row_per_move(db, founder_id):
    p = make(db, founder_id)
    for to in (states.AWAITING_APPROVAL, states.APPROVED, states.EXECUTING, states.SUCCEEDED):
        service.transition(db, p, to, actor_id=founder_id, now=NOW + timedelta(minutes=1))
    db.commit()
    rows = audit_of(db, p)
    assert [(r.from_status, r.to_status) for r in rows if r.event == "status"] == [
        ("draft", "awaiting_approval"), ("awaiting_approval", "approved"),
        ("approved", "executing"), ("executing", "succeeded")]
    assert rows[0].event == "created" or any(r.event == "created" for r in rows)
    assert all(r.actor_id == founder_id and r.action == "run_schedule" for r in rows)


def test_a_failed_run_is_audited_as_not_ok(db, founder_id):
    p = make(db, founder_id)
    for to in (states.AWAITING_APPROVAL, states.APPROVED, states.EXECUTING):
        service.transition(db, p, to, actor_id=founder_id, now=NOW)
    service.transition(db, p, states.FAILED, actor_id=None, now=NOW, detail={"error": "Timeout"})
    last = [r for r in audit_of(db, p) if r.to_status == states.FAILED][0]
    assert last.ok is False and last.detail == {"error": "Timeout"}


# ---- Hash binding -------------------------------------------------------------------------


def test_the_hash_ignores_key_order_and_changes_with_any_value():
    a = service.compute_params_hash("run_schedule", {"x": 1, "y": 2})
    assert a == service.compute_params_hash("run_schedule", {"y": 2, "x": 1})
    assert a != service.compute_params_hash("run_schedule", {"x": 1, "y": 3})
    assert a != service.compute_params_hash("move_job", {"x": 1, "y": 2})
    assert len(a) == 64


def test_an_approval_for_other_parameters_is_refused(db, founder_id):
    p = make(db, founder_id)
    service.check_params(p, p.params_hash)
    other = service.compute_params_hash("run_schedule", {**PARAMS, "to": "2026-12-31"})
    with pytest.raises(service.ParamsMismatch):
        service.check_params(p, other)


def test_parameters_edited_in_place_block_approval_and_execution(db, founder_id):
    p = make(db, founder_id)
    service.transition(db, p, states.AWAITING_APPROVAL, actor_id=founder_id, now=NOW)
    p.params = {**PARAMS, "society": "other"}  # an edit that did not make a new proposal
    with pytest.raises(service.ParamsMismatch):
        service.transition(db, p, states.APPROVED, actor_id=founder_id, now=NOW)
    assert p.status == states.AWAITING_APPROVAL


# ---- Expiry -------------------------------------------------------------------------------


def test_a_proposal_lives_five_minutes(db, founder_id):
    p = make(db, founder_id)
    assert p.expires_at == NOW + timedelta(minutes=5)
    assert not service.is_expired(p, NOW + timedelta(minutes=4, seconds=59))
    assert service.is_expired(p, NOW + timedelta(minutes=5))


def test_approval_and_execution_after_the_window_are_refused(db, founder_id):
    p = make(db, founder_id)
    service.transition(db, p, states.AWAITING_APPROVAL, actor_id=founder_id, now=NOW)
    late = NOW + timedelta(minutes=5)
    with pytest.raises(service.ProposalExpired):
        service.transition(db, p, states.APPROVED, actor_id=founder_id, now=late)
    service.transition(db, p, states.APPROVED, actor_id=founder_id, now=NOW)
    with pytest.raises(service.ProposalExpired):
        service.transition(db, p, states.EXECUTING, actor_id=founder_id, now=late)
    assert p.status == states.APPROVED


def test_the_sweep_expires_open_proposals_only(db, founder_id):
    open_ = [make(db, founder_id), make(db, founder_id), make(db, founder_id)]
    service.transition(db, open_[1], states.AWAITING_APPROVAL, actor_id=founder_id, now=NOW)
    service.transition(db, open_[2], states.AWAITING_APPROVAL, actor_id=founder_id, now=NOW)
    service.transition(db, open_[2], states.APPROVED, actor_id=founder_id, now=NOW)
    done = make(db, founder_id)
    for to in (states.AWAITING_APPROVAL, states.APPROVED, states.EXECUTING, states.SUCCEEDED):
        service.transition(db, done, to, actor_id=founder_id, now=NOW)
    running = make(db, founder_id)
    for to in (states.AWAITING_APPROVAL, states.APPROVED, states.EXECUTING):
        service.transition(db, running, to, actor_id=founder_id, now=NOW)
    fresh = make(db, founder_id, now=NOW + timedelta(minutes=10))
    db.commit()

    later = NOW + timedelta(minutes=6)
    assert service.expire_overdue(db, later) == 3
    db.commit()
    assert [p.status for p in open_] == [states.EXPIRED] * 3
    assert done.status == states.SUCCEEDED and running.status == states.EXECUTING
    assert fresh.status == states.DRAFT
    assert service.expire_overdue(db, later) == 0  # safe to run again
    expiry = [r for r in audit_of(db, open_[0]) if r.to_status == states.EXPIRED]
    assert len(expiry) == 1 and expiry[0].actor_id is None


# ---- Records ------------------------------------------------------------------------------


def test_one_approval_and_one_execution_per_proposal(db, founder_id):
    from sqlalchemy.exc import IntegrityError

    p = make(db, founder_id)
    db.add(ManiApproval(proposal_id=p.id, login_id=founder_id, params_hash=p.params_hash))
    db.add(ManiExecution(proposal_id=p.id, idempotency_key=f"proposal:{p.id}"))
    db.commit()
    db.add(ManiExecution(proposal_id=p.id, idempotency_key="another"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    q = make(db, founder_id)
    db.add(ManiExecution(proposal_id=q.id, idempotency_key=f"proposal:{p.id}"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_the_database_refuses_an_unknown_status(db, founder_id):
    from sqlalchemy.exc import IntegrityError

    p = make(db, founder_id)
    db.commit()
    p.status = "approvedish"
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_a_proposal_outlives_the_chat_that_made_it(db, founder_id):
    c = ManiConversation(login_id=founder_id, title="x")
    db.add(c)
    db.commit()
    run = ManiRun(conversation_id=c.id, status="succeeded")
    db.add(run)
    db.commit()
    p = make(db, founder_id, conversation_id=c.id, run_id=run.id)
    db.commit()
    delete_conversation_rows(db, [c.id])
    db.commit()
    db.expire_all()
    kept = db.get(ManiProposal, p.id)
    assert kept is not None and kept.conversation_id is None and kept.run_id is None


# ---- Retention ----------------------------------------------------------------------------


def finish(db, founder_id, when):
    p = make(db, founder_id, now=when)
    for to in (states.AWAITING_APPROVAL, states.APPROVED, states.EXECUTING, states.SUCCEEDED):
        service.transition(db, p, to, actor_id=founder_id, now=when)
    db.add(ManiApproval(proposal_id=p.id, login_id=founder_id, params_hash=p.params_hash, approved_at=when))
    db.add(ManiExecution(proposal_id=p.id, idempotency_key=f"proposal:{p.id}", started_at=when))
    db.commit()
    return p


def test_the_audit_is_kept_three_months_and_then_deleted(db, founder_id):
    young = finish(db, founder_id, NOW - timedelta(days=91))
    old = finish(db, founder_id, NOW - timedelta(days=93))
    result = sweep_actions(db, NOW, 92)
    assert result["proposals_deleted"] == 1 and result["audit_deleted"] >= 5
    db.expire_all()
    assert db.get(ManiProposal, young.id) is not None and db.get(ManiProposal, old.id) is None
    assert len(audit_of(db, young)) == 5
    assert db.scalars(select(ManiApproval).where(ManiApproval.proposal_id == old.id)).first() is None
    assert db.scalars(select(ManiExecution).where(ManiExecution.proposal_id == old.id)).first() is None
    assert sweep_actions(db, NOW, 92) == {"proposals_expired": 0, "audit_deleted": 0, "proposals_deleted": 0}


def test_an_unfinished_old_proposal_is_expired_first_then_deleted_on_a_later_run(db, founder_id):
    p = make(db, founder_id, now=NOW - timedelta(days=200))
    db.commit()
    first = sweep_actions(db, NOW, 92)
    assert first["proposals_expired"] == 1
    db.expire_all()
    # Expiry is a fresh change, so the 3 months run from now, not from the old creation.
    assert db.get(ManiProposal, p.id).status == states.EXPIRED
    assert first["proposals_deleted"] == 0
    assert sweep_actions(db, NOW + timedelta(days=93), 92)["proposals_deleted"] == 1
