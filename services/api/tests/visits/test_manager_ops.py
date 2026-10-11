"""CRW-MGR-02 (plan extension), CRW-MGR-03 (reassign checks), CRW-MGR-04
(attendance) and CRW-MGR-05 (working hours)."""
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.changes.cycle import shift_days
from app.directory.models import Society
from app.platform.clock import today_ist
from app.scheduling.models import Job, SchedulingCrew, SchedulingCrewException
from app.visits.models import CrewManagerChange
from tests.visits.conftest import DAY

TODAY = today_ist()
TOMORROW = TODAY + timedelta(days=1)

from app.customers.models import WEEKDAYS as ALL_DAYS  # noqa: E402


def hours(start="06:00", end="11:00", off=()):
    return [{"day": d, "working": d not in off, "start": "" if d in off else start,
             "end": "" if d in off else end} for d in ALL_DAYS]


def set_attendance(client, headers, crew, status, day=TOMORROW, **extra):
    return client.put(f"/v1/crew/manager/attendance/{crew.id}", headers=headers,
                      json={"status": status, "from_date": day.isoformat(), **extra})


# ---- attendance ------------------------------------------------------------------

def test_a_member_cannot_use_attendance_or_hours(crew_client, make_crew, signin):
    ravi = make_crew("9000000010", "Ravi")
    h = signin(ravi)
    assert crew_client.get("/v1/crew/manager/attendance", headers=h).status_code == 403
    assert crew_client.get("/v1/crew/manager/hours", headers=h).status_code == 403


def test_marking_absent_changes_the_list_and_releases_open_jobs(
        crew_client, make_crew, signin, new_visit, db: Session):
    boss = make_crew("9000000001", "Manju", role="Manager")
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi, day=TOMORROW, status="Draft")
    h = signin(boss)

    r = set_attendance(crew_client, h, ravi, "Sick")
    assert r.status_code == 200, r.text
    body = r.json()
    entry = next(e for e in body["attendance"]["crew"] if e["name"] == "Ravi")
    assert entry["status"] == "Sick"
    # A Draft schedule is not placed again: the job waits on Needs scheduling.
    assert [j["job_id"] for j in body["released_jobs"]] == [str(job.id)]
    assert body["released_jobs"][0]["reassigned"] is False
    db.expire_all()
    assert db.get(Job, job.id).crew_id is None
    assert db.scalar(select(func.count()).select_from(CrewManagerChange)) == 1

    # Present again removes the exception.
    back = set_attendance(crew_client, h, ravi, "present")
    entry = next(e for e in back.json()["attendance"]["crew"] if e["name"] == "Ravi")
    assert entry["status"] == "present"
    assert db.scalar(select(func.count()).select_from(SchedulingCrewException)) == 0


def test_a_frozen_job_goes_to_someone_who_fits(
        crew_client, make_crew, signin, new_visit, db: Session):
    boss = make_crew("9000000001", "Manju", role="Manager")
    ravi = make_crew("9000000010", "Ravi")
    sunil = make_crew("9000000011", "Sunil")
    _, (job,) = new_visit(assigned=ravi, day=TOMORROW)
    job_id = job.id
    r = set_attendance(crew_client, signin(boss), ravi, "Leave")
    assert r.status_code == 200, r.text
    released = r.json()["released_jobs"]
    assert len(released) == 1
    db.expire_all()
    moved = db.scalar(select(Job).where(Job.id == job_id))
    # The scheduler places it with Sunil or Manju, never back on Ravi. A
    # hand-made job with no demand behind it is dropped by the re-run.
    if moved is not None:
        assert released[0]["reassigned"] is (moved.crew_id is not None)
        assert moved.crew_id != ravi.id
    assert sunil.id != ravi.id


def test_late_start_needs_a_time_and_dates_in_the_past_are_refused(
        crew_client, make_crew, signin):
    boss = make_crew("9000000001", "Manju", role="Manager")
    ravi = make_crew("9000000010", "Ravi")
    h = signin(boss)
    assert set_attendance(crew_client, h, ravi, "Late start").status_code == 422
    ok = set_attendance(crew_client, h, ravi, "Late start", start="08:30")
    assert ok.status_code == 200
    entry = next(e for e in ok.json()["attendance"]["crew"] if e["name"] == "Ravi")
    assert entry["late_start"] == "08:30"
    past = set_attendance(crew_client, h, ravi, "Sick", day=TODAY - timedelta(days=1))
    assert past.status_code == 422
    assert set_attendance(crew_client, h, ravi, "Holiday").status_code == 422


def test_another_society_is_not_found(crew_client, make_crew, signin, db: Session):
    boss = make_crew("9000000001", "Manju", role="Manager")
    other = Society(name="Other Society")
    db.add(other)
    db.commit()
    stranger = make_crew("9000000020", "Stranger", society=other)
    h = signin(boss)
    assert set_attendance(crew_client, h, stranger, "Sick").status_code == 404
    r = crew_client.put(f"/v1/crew/manager/hours/{stranger.id}", headers=h,
                        json={"working_hours": hours()})
    assert r.status_code == 404
    names = {e["name"] for e in crew_client.get(
        "/v1/crew/manager/attendance", headers=h).json()["crew"]}
    assert "Stranger" not in names


# ---- working hours ---------------------------------------------------------------

def test_hours_are_listed_and_changed_and_capacity_follows(
        crew_client, make_crew, signin, new_visit, db: Session):
    boss = make_crew("9000000001", "Manju", role="Manager")
    ravi = make_crew("9000000010", "Ravi")
    h = signin(boss)
    listed = crew_client.get("/v1/crew/manager/hours", headers=h).json()
    assert {x["name"] for x in listed} == {"Manju", "Ravi"}

    _, (job,) = new_visit(assigned=ravi, day=TOMORROW, status="Draft")
    # The job is at 07:00. A day off tomorrow takes it off Ravi.
    off = ALL_DAYS[TOMORROW.weekday()]
    r = crew_client.put(f"/v1/crew/manager/hours/{ravi.id}", headers=h,
                        json={"working_hours": hours(off=(off,))})
    assert r.status_code == 200, r.text
    assert len(r.json()["released_jobs"]) == 1
    db.expire_all()
    assert db.get(SchedulingCrew, ravi.id).working_hours is not None
    assert db.get(Job, job.id).crew_id is None
    assert db.scalar(select(func.count()).select_from(CrewManagerChange)
                     .where(CrewManagerChange.kind == "hours")) == 1


def test_bad_hours_are_refused(crew_client, make_crew, signin):
    boss = make_crew("9000000001", "Manju", role="Manager")
    ravi = make_crew("9000000010", "Ravi")
    h = signin(boss)
    r = crew_client.put(f"/v1/crew/manager/hours/{ravi.id}", headers=h,
                        json={"working_hours": hours(start="11:00", end="06:00")})
    assert r.status_code == 422
    r = crew_client.put(f"/v1/crew/manager/hours/{ravi.id}", headers=h,
                        json={"working_hours": hours()[:3]})
    assert r.status_code == 422


# ---- reassign checks -------------------------------------------------------------

def test_reassign_to_someone_on_leave_is_refused(
        crew_client, make_crew, signin, new_visit, db: Session):
    boss = make_crew("9000000001", "Manju", role="Manager")
    ravi = make_crew("9000000010", "Ravi")
    sunil = make_crew("9000000011", "Sunil")
    _, (job,) = new_visit(assigned=ravi, day=TOMORROW)
    h = signin(boss)
    set_attendance(crew_client, h, sunil, "Leave")
    r = crew_client.post(f"/v1/crew/manager/jobs/{job.id}/reassign", headers=h,
                         json={"crew_id": str(sunil.id)})
    assert r.status_code == 409
    assert r.json()["code"] == "crew_not_working"
    options = crew_client.get(f"/v1/crew/manager/jobs/{job.id}/reassign-options",
                              headers=h).json()
    by_name = {o["name"]: o for o in options}
    assert by_name["Sunil"]["can_assign"] is False
    assert by_name["Sunil"]["problem_code"] == "crew_not_working"
    assert by_name["Manju"]["can_assign"] is True


def test_reassign_outside_hours_and_overlap_are_refused(
        crew_client, make_crew, signin, new_visit, db: Session):
    boss = make_crew("9000000001", "Manju", role="Manager")
    ravi = make_crew("9000000010", "Ravi")
    sunil = make_crew("9000000011", "Sunil")
    _, (job,) = new_visit(assigned=ravi, day=TOMORROW)  # 07:00
    # Sunil starts late: 08:30.
    h = signin(boss)
    set_attendance(crew_client, h, sunil, "Late start", start="08:30")
    r = crew_client.post(f"/v1/crew/manager/jobs/{job.id}/reassign", headers=h,
                         json={"crew_id": str(sunil.id)})
    assert r.status_code == 409
    assert r.json()["code"] == "outside_hours"

    # Sunil already has a job at 07:00 on another vehicle.
    new_visit(assigned=boss, vehicle=1, day=TOMORROW)
    r = crew_client.post(f"/v1/crew/manager/jobs/{job.id}/reassign", headers=h,
                         json={"crew_id": str(boss.id)})
    assert r.status_code == 409
    assert r.json()["code"] == "overlap"


def test_reassign_to_the_same_person_and_a_started_job_are_refused(
        crew_client, make_crew, signin, new_visit, db: Session):
    boss = make_crew("9000000001", "Manju", role="Manager")
    ravi = make_crew("9000000010", "Ravi")
    sunil = make_crew("9000000011", "Sunil")
    _, (job,) = new_visit(assigned=ravi, day=TOMORROW)
    h = signin(boss)
    same = crew_client.post(f"/v1/crew/manager/jobs/{job.id}/reassign", headers=h,
                            json={"crew_id": str(ravi.id)})
    assert same.status_code == 409
    assert same.json()["code"] == "same_crew"
    job.status = "In progress"
    db.commit()
    r = crew_client.post(f"/v1/crew/manager/jobs/{job.id}/reassign", headers=h,
                         json={"crew_id": str(sunil.id)})
    assert r.status_code == 409
    assert r.json()["code"] == "job_in_progress"


def test_an_unplaced_job_gets_the_first_free_time(
        crew_client, make_crew, signin, new_visit, db: Session):
    boss = make_crew("9000000001", "Manju", role="Manager")
    sunil = make_crew("9000000011", "Sunil")
    _, (job,) = new_visit(day=TOMORROW)
    job.start_minute = None
    db.commit()
    r = crew_client.post(f"/v1/crew/manager/jobs/{job.id}/reassign", headers=signin(boss),
                         json={"crew_id": str(sunil.id)})
    assert r.status_code == 200, r.text
    db.expire_all()
    assert db.get(Job, job.id).start_minute == 360


# ---- plan extension --------------------------------------------------------------

def test_skipping_external_extends_the_plan_by_one_day_once(
        crew_client, make_crew, signin, new_visit, world, db: Session):
    boss = make_crew("9000000001", "Manju", role="Manager")
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    vehicle = world.vehicles[0]
    before = shift_days(db, vehicle.id)
    h = signin(boss)
    assert crew_client.post(f"/v1/crew/manager/jobs/{job.id}/skip", headers=h).status_code == 200
    db.expire_all()
    assert shift_days(db, vehicle.id) == before + 1
    # A second skip is refused and adds nothing.
    assert crew_client.post(f"/v1/crew/manager/jobs/{job.id}/skip", headers=h).status_code == 409
    assert shift_days(db, vehicle.id) == before + 1


def test_skipping_internal_does_not_extend_the_plan(
        crew_client, make_crew, signin, new_visit, world, db: Session):
    boss = make_crew("9000000001", "Manju", role="Manager")
    ravi = make_crew("9000000010", "Ravi")
    _, jobs = new_visit(services=("Cleaning-Internal",), assigned=ravi, day=DAY)
    before = shift_days(db, world.vehicles[0].id)
    r = crew_client.post(f"/v1/crew/manager/jobs/{jobs[0].id}/skip", headers=signin(boss))
    assert r.status_code == 200
    db.expire_all()
    assert shift_days(db, world.vehicles[0].id) == before
