"""Several working slots a day, and hours that start as the society's working
slots (ADM-CRW-25)."""
from sqlalchemy import select

from app.directory.models import WorkingSlot
from tests.crew.test_crew import DAYS, HOURS, auth, body, create, login


def admin(client):
    return auth(login(client, "admin")["access_token"])


def with_extra(day, slots):
    return [dict(h, extra_slots=slots) if h["day"] == day else h for h in HOURS]


def test_a_crew_member_can_have_two_slots_in_a_day(client, society):
    r = create(client, society, working_hours=with_extra(
        "Monday", [{"start": "17:00", "end": "19:00"}]))
    assert r.status_code == 201, r.text
    monday = next(h for h in r.json()["crew"]["working_hours"] if h["day"] == "Monday")
    assert (monday["start"], monday["end"]) == ("07:00", "15:00")
    assert monday["extra_slots"] == [{"start": "17:00", "end": "19:00"}]


def test_slots_must_not_overlap_or_touch(client, society):
    for slots in ([{"start": "14:00", "end": "19:00"}],       # overlaps the first slot
                  [{"start": "15:00", "end": "19:00"}],       # touches it
                  [{"start": "19:00", "end": "17:00"}],       # backwards
                  [{"start": "17:00", "end": "19:00"}, {"start": "18:00", "end": "20:00"}]):
        r = create(client, society, working_hours=with_extra("Monday", slots))
        assert r.status_code == 422, (slots, r.text)
        assert "working_hours" in r.json()["fields"]


def test_a_day_off_keeps_no_extra_slots(client, society):
    hours = [dict(h, extra_slots=[{"start": "17:00", "end": "19:00"}]) if h["day"] == "Sunday"
             else h for h in HOURS]  # Sunday is a day off in HOURS
    r = create(client, society, working_hours=hours)
    assert r.status_code == 201, r.text
    sunday = next(h for h in r.json()["crew"]["working_hours"] if h["day"] == "Sunday")
    assert sunday["working"] is False and sunday["extra_slots"] == []


def add_slot(db, society, service, start, end, days):
    db.add(WorkingSlot(society_id=society.id, service=service, start_minute=start,
                       end_minute=end, days=days))
    db.commit()


def test_default_hours_come_from_the_societys_working_slots(client, db, society):
    for slot in db.scalars(select(WorkingSlot).where(WorkingSlot.society_id == society.id)):
        db.delete(slot)
    db.commit()
    add_slot(db, society, "Cleaning-External", 300, 780, [0, 1, 2, 3, 4, 5, 6])  # 05:00-13:00
    add_slot(db, society, "Cleaning-External", 1020, 1140, [0, 1, 2, 3, 4])  # 17:00-19:00 Mon-Fri
    add_slot(db, society, "Deep Spa", 0, 1440, [0, 1, 2, 3, 4, 5, 6])  # not a cleaning slot
    r = client.get("/v1/admin/crew/default-hours", params={"society_id": str(society.id)},
                   headers=admin(client))
    assert r.status_code == 200, r.text
    days = {h["day"]: h for h in r.json()}
    assert [days["Monday"]["start"], days["Monday"]["end"]] == ["05:00", "13:00"]
    assert days["Monday"]["extra_slots"] == [{"start": "17:00", "end": "19:00"}]
    assert days["Saturday"]["extra_slots"] == [] and days["Saturday"]["working"] is True


def test_overlapping_society_slots_are_joined_and_a_day_without_slots_is_off(client, db, society):
    for slot in db.scalars(select(WorkingSlot).where(WorkingSlot.society_id == society.id)):
        db.delete(slot)
    db.commit()
    add_slot(db, society, "Cleaning-External", 300, 660, [0])
    add_slot(db, society, "Cleaning-Internal", 600, 780, [0])  # overlaps: joined to 05:00-13:00
    r = client.get("/v1/admin/crew/default-hours", params={"society_id": str(society.id)},
                   headers=admin(client))
    days = {h["day"]: h for h in r.json()}
    assert (days["Monday"]["start"], days["Monday"]["end"], days["Monday"]["extra_slots"]) == (
        "05:00", "13:00", [])
    assert days["Tuesday"]["working"] is False


def test_a_new_crew_member_without_hours_gets_the_societys_slots(client, db, society):
    for slot in db.scalars(select(WorkingSlot).where(WorkingSlot.society_id == society.id)):
        db.delete(slot)
    db.commit()
    add_slot(db, society, "Cleaning-External", 360, 720, [0, 1, 2, 3, 4, 5, 6])  # 06:00-12:00
    data = body(society)
    data.pop("working_hours")
    r = client.post("/v1/admin/crew", json=data, headers=admin(client))
    assert r.status_code == 201, r.text
    hours = r.json()["crew"]["working_hours"]
    assert [h["day"] for h in hours] == DAYS
    assert all((h["start"], h["end"]) == ("06:00", "12:00") for h in hours)
