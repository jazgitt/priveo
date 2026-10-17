"""A crew member's society as a dated record: moves from a date, a history that
never changes, and cancelling a move that has not happened (ADM-CRW-13,
ADM-CRW-22)."""
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.crew.models import CrewMember, CrewSocietyAssignment
from app.crew.society_moves import apply_due_moves
from app.directory.models import Society
from app.platform.clock import today_ist
from app.scheduling.models import SchedulingCrew
from tests.crew.test_crew import create
from tests.test_api import auth, login


@pytest.fixture
def other(db):
    row = Society(name="Palm Court", sector="Sector 2")
    db.add(row)
    db.commit()
    return row


def admin(client):
    return auth(login(client, "admin")["access_token"])


def history(client, crew_id):
    r = client.get(f"/v1/admin/crew/{crew_id}/society-history", headers=admin(client))
    assert r.status_code == 200, r.text
    return r.json()


def move(client, crew_id, society, on, **extra):
    return client.post(
        f"/v1/admin/crew/{crew_id}/society", headers=admin(client),
        json={"society_id": str(society.id), "effective_from": on.isoformat(), **extra})


def test_onboarding_records_the_first_stay(client, society):
    crew = create(client, society).json()["crew"]
    stays = history(client, crew["id"])
    assert [(s["society"], s["effective_to"], s["pending"]) for s in stays] == [
        ("Green Meadows", None, False)]
    assert stays[0]["effective_from"] == today_ist().isoformat()


def test_a_later_move_keeps_the_past_and_takes_effect_on_its_date(client, db, society, other):
    crew = create(client, society).json()["crew"]
    day = today_ist() + timedelta(days=10)
    r = move(client, crew["id"], other, day)
    assert r.status_code == 200, r.text
    # Until the date the crew member is still in the old society.
    assert r.json()["crew"]["society"] == "Green Meadows"
    stays = history(client, crew["id"])
    assert [(s["society"], s["pending"]) for s in stays] == [
        ("Green Meadows", False), ("Palm Court", True)]
    assert stays[0]["effective_to"] == (day - timedelta(days=1)).isoformat()
    first = stays[0]["effective_from"]

    # The day comes: the crew member and the scheduler's record follow.
    assert apply_due_moves(db, day) == 1
    member = db.scalar(select(CrewMember).where(CrewMember.id == uuid.UUID(crew["id"])))
    assert member.society_id == other.id
    sc = db.scalar(select(SchedulingCrew).where(SchedulingCrew.login_id == member.login_id))
    assert sc.society_id == other.id
    # Applying again changes nothing, and the earlier stay is exactly as it was.
    assert apply_due_moves(db, day) == 0
    stays = history(client, crew["id"])
    assert stays[0]["society"] == "Green Meadows" and stays[0]["effective_from"] == first
    assert stays[0]["effective_to"] == (day - timedelta(days=1)).isoformat()
    # The move was applied as of `day`; the history still compares with the real
    # today, so the new stay is shown as not started yet.
    assert stays[1]["effective_to"] is None and stays[1]["pending"] is True


def test_a_move_for_today_takes_effect_at_once(client, db, society, other):
    crew = create(client, society).json()["crew"]
    r = move(client, crew["id"], other, today_ist())
    assert r.status_code == 200, r.text
    assert r.json()["crew"]["society"] == "Palm Court"
    sc = db.scalar(select(SchedulingCrew).join(
        CrewMember, CrewMember.login_id == SchedulingCrew.login_id).where(
        CrewMember.id == uuid.UUID(crew["id"])))
    assert sc.society_id == other.id


def test_the_past_cannot_be_changed_and_the_society_must_differ(client, society, other):
    crew = create(client, society).json()["crew"]
    past = move(client, crew["id"], other, today_ist() - timedelta(days=1))
    assert past.status_code == 422 and "effective_from" in past.json()["fields"]
    same = move(client, crew["id"], society, today_ist() + timedelta(days=3))
    assert same.status_code == 422 and "society_id" in same.json()["fields"]


def test_only_one_move_can_be_waiting_and_it_can_be_cancelled(client, db, society, other):
    crew = create(client, society).json()["crew"]
    day = today_ist() + timedelta(days=5)
    assert move(client, crew["id"], other, day).status_code == 200
    again = move(client, crew["id"], other, day + timedelta(days=2))
    assert again.status_code == 409 and again.json()["code"] == "move_pending"

    pending = history(client, crew["id"])[1]
    r = client.delete(f"/v1/admin/crew/{crew['id']}/society-moves/{pending['id']}",
                      headers=admin(client))
    assert r.status_code == 200, r.text
    assert [s["society"] for s in history(client, crew["id"])] == ["Green Meadows"]
    # The first stay is not a move and cannot be cancelled.
    first = history(client, crew["id"])[0]
    gone = client.delete(f"/v1/admin/crew/{crew['id']}/society-moves/{first['id']}",
                         headers=admin(client))
    assert gone.status_code == 409 and gone.json()["code"] == "move_done"
    assert db.scalar(select(CrewSocietyAssignment).where(
        CrewSocietyAssignment.crew_id == uuid.UUID(crew["id"]))) is not None


def test_a_trainee_needs_a_member_of_the_new_society(client, society, other):
    member = create(client, society, mobile="9000000601", name="Asha Rao").json()["crew"]
    trainee = create(client, society, mobile="9000000602", name="Ravi Kumar", role="Trainee",
                     paired_member_id=member["id"]).json()["crew"]
    day = today_ist() + timedelta(days=4)
    r = move(client, trainee["id"], other, day)
    assert r.status_code == 422 and "paired_member_id" in r.json()["fields"]
    # The paired Member must belong to the new society.
    new_member = create(client, other, mobile="9000000603", name="Dev Anand").json()["crew"]
    ok = move(client, trainee["id"], other, day, paired_member_id=new_member["id"])
    assert ok.status_code == 200, ok.text


def test_a_members_trainees_move_with_them_on_the_same_date(client, db, society, other):
    member = create(client, society, mobile="9000000611", name="Asha Rao").json()["crew"]
    trainee = create(client, society, mobile="9000000612", name="Ravi Kumar", role="Trainee",
                     paired_member_id=member["id"]).json()["crew"]
    day = today_ist() + timedelta(days=4)
    r = move(client, member["id"], other, day)
    assert r.status_code == 200, r.text
    # The Trainee has the same move waiting.
    assert [(s["society"], s["effective_from"], s["pending"])
            for s in history(client, trainee["id"])][1:] == [("Palm Court", day.isoformat(), True)]
    # On the date both are in the new society and the pairing is kept.
    assert apply_due_moves(db, day) == 2
    rows = {c.name: c for c in db.scalars(select(CrewMember))}
    assert rows["Asha Rao"].society_id == other.id and rows["Ravi Kumar"].society_id == other.id
    t_sc = db.scalar(select(SchedulingCrew).where(
        SchedulingCrew.login_id == rows["Ravi Kumar"].login_id))
    m_sc = db.scalar(select(SchedulingCrew).where(
        SchedulingCrew.login_id == rows["Asha Rao"].login_id))
    assert t_sc.society_id == other.id and t_sc.paired_member_id == m_sc.id


def test_cancelling_a_members_move_cancels_their_trainees_move(client, society, other):
    member = create(client, society, mobile="9000000621", name="Asha Rao").json()["crew"]
    trainee = create(client, society, mobile="9000000622", name="Ravi Kumar", role="Trainee",
                     paired_member_id=member["id"]).json()["crew"]
    move(client, member["id"], other, today_ist() + timedelta(days=4))
    pending = history(client, member["id"])[1]
    r = client.delete(f"/v1/admin/crew/{member['id']}/society-moves/{pending['id']}",
                      headers=admin(client))
    assert r.status_code == 200, r.text
    assert [s["society"] for s in history(client, trainee["id"])] == ["Green Meadows"]


def test_a_trainee_with_their_own_move_waiting_blocks_the_members_move(client, society, other):
    member = create(client, society, mobile="9000000631", name="Asha Rao").json()["crew"]
    trainee = create(client, society, mobile="9000000632", name="Ravi Kumar", role="Trainee",
                     paired_member_id=member["id"]).json()["crew"]
    new_member = create(client, other, mobile="9000000633", name="Dev Anand").json()["crew"]
    day = today_ist() + timedelta(days=4)
    assert move(client, trainee["id"], other, day,
                paired_member_id=new_member["id"]).status_code == 200
    r = move(client, member["id"], other, day)
    assert r.status_code == 409 and r.json()["code"] == "trainee_move_pending"
