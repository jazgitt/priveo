"""P02: catalogue edits cannot rewrite an issued/completed job definition."""
from datetime import timedelta

from sqlalchemy import select

from app.directory.models import ChecklistItem
from app.directory.seed import seed_defaults
from app.visits.checklists import items_for_job
from tests.visits.conftest import DAY
from tests.visits.test_crew_jobs import tick_all


def test_issued_checklist_keeps_labels_order_and_required_items(
        crew_client, make_crew, signin, new_visit, db):
    seed_defaults(db)
    member = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=member)
    headers = signin(member)
    url = f"/v1/crew/jobs/{job.id}"
    before = crew_client.get(url, headers=headers).json()["checklist"]
    glass = db.scalar(select(ChecklistItem).where(
        ChecklistItem.service == job.service, ChecklistItem.key == "glass"))
    glass.label, glass.active, glass.sort_order = "Changed glass", False, 99
    db.add(ChecklistItem(service=job.service, key="new", label="New requirement", sort_order=-1))
    db.commit()
    assert crew_client.get(url, headers=headers).json()["checklist"] == before
    # The deactivated catalogue key remains valid on this issued job.
    tick_all(crew_client, headers, str(job.id))
    detail = crew_client.get(url, headers=headers).json()
    assert all(i["checked_at"] for i in detail["checklist"])
    assert not any("checklist item" in m for m in detail["missing"])
    assert crew_client.put(f"{url}/checklist/new", headers=headers,
                           json={"checked": True}).status_code == 404
    _, (future,) = new_visit(assigned=member, day=DAY + timedelta(days=1))
    db.expire_all()
    assert "new" in {i.key for i in items_for_job(db, future)}
    assert "glass" not in {i.key for i in items_for_job(db, future)}


def test_customer_completed_history_uses_snapshot_and_original_tick_times(
        db, new_visit, make_crew, signin, crew_client):
    from app.customer_reads.sql_repository import SqlVisitReadRepository

    seed_defaults(db)
    member = make_crew("9000000010", "Ravi")
    visit, (job,) = new_visit(assigned=member)
    tick_all(crew_client, signin(member), str(job.id))
    db.expire_all()
    job.status, visit.status = "Completed", "Completed"
    db.commit()
    # Exercise the same projection used by customer visit/history reads.
    repo = SqlVisitReadRepository(db)
    before = repo.jobs([str(visit.id)])[0].checklist
    row = db.scalar(select(ChecklistItem).where(
        ChecklistItem.service == job.service, ChecklistItem.key == "body"))
    row.label, row.sort_order = "Renamed body", 100
    db.add(ChecklistItem(service=job.service, key="later", label="Later", sort_order=-1))
    db.commit()
    after = repo.jobs([str(visit.id)])[0].checklist
    assert [(i.key, i.label, i.checked_at) for i in after] == [
        (i.key, i.label, i.checked_at) for i in before]


def test_legacy_backfill_marks_unknown_labels_and_excludes_new_items_from_completed_work(
        db, new_visit, make_crew, signin, crew_client, monkeypatch):
    import importlib.util
    from contextlib import nullcontext
    from pathlib import Path
    from types import SimpleNamespace

    seed_defaults(db)
    member = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=member)
    tick_all(crew_client, signin(member), str(job.id))
    db.expire_all()
    job.checklist_snapshot, job.status = None, "Completed"
    db.add(ChecklistItem(service=job.service, key="later", label="Later", sort_order=-1))
    db.commit()
    path = Path(__file__).resolve().parents[2] / "migrations/versions/20261013_0025_job_checklist_snapshot.py"
    spec = importlib.util.spec_from_file_location("snapshot_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    monkeypatch.setattr(migration.op, "get_bind", lambda: db.connection())
    # Current test schema already has the column: isolate data backfill here.
    monkeypatch.setattr(migration.op, "batch_alter_table", lambda _: nullcontext(
        SimpleNamespace(add_column=lambda _: None)))
    migration.upgrade()
    db.commit()
    db.expire_all()
    assert job.checklist_snapshot["legacy"] is True
    assert "later" not in {i["key"] for i in job.checklist_snapshot["items"]}
    assert len(job.checklist_snapshot["items"]) == 5


def test_completed_calendar_has_finish_and_check_summary(db, new_visit, make_crew, signin, crew_client):
    from app.customer_reads.service import CustomerReads
    from app.customer_reads.sql_repository import SqlVisitReadRepository
    from app.customers.models import Customer, Vehicle
    from app.platform.db import utcnow
    from app.visits.models import JobTiming

    member = make_crew("9000000010", "Ravi")
    visit, (job,) = new_visit(assigned=member)
    tick_all(crew_client, signin(member), str(job.id))
    db.expire_all()
    job.status, visit.status = "Completed", "Completed"
    finished = utcnow()
    timing = db.get(JobTiming, job.id)
    timing.finished_at = finished
    db.commit()
    owner = db.get(Customer, db.get(Vehicle, visit.vehicle_id).customer_id)
    reads = CustomerReads(db, SqlVisitReadRepository(db))
    month = reads.calendar(owner.login_id, DAY.strftime('%Y-%m'), str(visit.vehicle_id))
    day = next(d for d in month.visits if d.visit_id == str(visit.id))
    assert day.checklist_done == day.checklist_total == 5
    assert day.finished_at == finished
