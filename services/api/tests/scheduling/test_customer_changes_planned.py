"""A skip, a pause or a cutoff time made before a date is planned is kept when
the date is planned (SKIP-, PAUSE-, CAL-08)."""
from datetime import date, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.changes.models import ScheduleChange
from app.scheduling.models import Job, Visit
from tests.scheduling.conftest import SUNDAY


def test_changes_made_before_planning_are_kept(api, world, run_week):
    world.add_crew(end=600)
    car = world.add_vehicle(cutoff=time(8, 0))
    base = {"customer_id": world.customer.id, "vehicle_id": car.id, "actor": "customer"}
    world.db.add_all([
        ScheduleChange(kind="skip", start_date=SUNDAY, end_date=SUNDAY, status="Active", **base),
        ScheduleChange(kind="pause", start_date=date(2026, 10, 19),
                       end_date=date(2026, 10, 19), status="Active", **base),
        ScheduleChange(kind="cutoff", start_date=date(2026, 10, 20),
                       end_date=date(2026, 10, 20), cutoff_time=time(9, 30),
                       status="Applied", **base),
    ])
    world.db.commit()
    run_week(days=3)
    with Session(world.db.get_bind()) as db:
        rows = {v.date: j for j, v in db.execute(
            select(Job, Visit).join(Visit, Job.visit_id == Visit.id)).all()}
    assert rows[SUNDAY].status == "Skipped"
    assert rows[date(2026, 10, 19)].status == "Skipped"
    assert rows[date(2026, 10, 20)].status == "Scheduled"
    assert rows[date(2026, 10, 20)].finish_by_minute == 9 * 60 + 30


def test_skipped_and_paused_jobs_are_listed_with_why(api, admin, world, run_week):
    # ADM-SCH-36: the Skipped and paused tab says whether a job was paused or
    # skipped, and by whom.
    world.add_crew(end=600)
    car = world.add_vehicle(cutoff=time(8, 0))
    base = {"customer_id": world.customer.id, "vehicle_id": car.id}
    world.db.add_all([
        ScheduleChange(kind="skip", start_date=SUNDAY, end_date=SUNDAY, status="Active",
                       actor="customer", **base),
        ScheduleChange(kind="pause", start_date=date(2026, 10, 19),
                       end_date=date(2026, 10, 20), status="Active", actor="admin", **base),
    ])
    world.db.commit()
    run_week(days=3)

    params = {"society_id": str(world.society.id), "date_from": "2026-10-18",
              "date_to": "2026-10-19"}
    r = api.get("/v1/admin/scheduling/skipped", headers=admin, params=params)
    assert r.status_code == 200, r.text
    rows = {j["date"]: j for j in r.json()}
    assert set(rows) == {"2026-10-18", "2026-10-19"}
    assert rows["2026-10-18"]["skip_kind"] == "Skipped"
    assert rows["2026-10-18"]["skip_reason"] == "Skipped by the customer"
    assert rows["2026-10-19"]["skip_kind"] == "Paused"
    assert rows["2026-10-19"]["skip_reason"] == "Paused by the admin, 19-Oct-26 to 20-Oct-26"

    params["date_to"] = "2026-10-17"
    r = api.get("/v1/admin/scheduling/skipped", headers=admin, params=params)
    assert r.status_code == 422
