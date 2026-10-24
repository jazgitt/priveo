"""A-04: crew outcomes and manager reassignment leave a directory-audit row."""
from sqlalchemy import select

from app.directory.models import DirectoryAudit
from tests.visits.conftest import upload_file
from tests.visits.test_crew_jobs import tick_all


def rows(db, entity="job"):
    db.expire_all()
    return list(db.scalars(select(DirectoryAudit).where(DirectoryAudit.entity == entity)
                           .order_by(DirectoryAudit.at)))


def test_complete_and_not_done_are_audited_without_the_remark_text(
        crew_client, make_crew, signin, new_visit, db):
    ravi = make_crew("9000000010", "Ravi")
    _, jobs = new_visit(["Cleaning-External", "Cleaning-Internal"], assigned=ravi)
    headers = signin(ravi)
    first = str(jobs[0].id)
    tick_all(crew_client, headers, first)
    for kind, stage in (("photo", "Before"), ("photo", "After"), ("video", "During")):
        upload_file(crew_client, headers, first, kind=kind, stage=stage)
    assert crew_client.post(f"/v1/crew/jobs/{first}/complete", headers=headers).status_code == 200
    remark = "Owner Asha said call 9876543210"
    r = crew_client.post(f"/v1/crew/jobs/{jobs[1].id}/could-not-complete", headers=headers,
                         json={"reason_key": "car_locked", "note": remark})
    assert r.status_code == 200, r.text
    done, missed = rows(db)
    assert done.action == "complete" and done.entity_id == first
    assert done.admin_login_id is not None and done.detail["status"][1] == "Completed"
    assert missed.action == "not_done" and missed.admin_login_id is not None
    assert missed.detail["reason_key"] == "car_locked"
    assert missed.detail["remark_length"] == len(remark)
    assert remark not in str(missed.detail) and len(missed.entity) <= 24


def test_manager_reassign_is_audited_with_old_and_new_crew(
        crew_client, make_crew, signin, new_visit, db):
    boss = make_crew("9000000001", "Manju", role="Manager")
    ravi = make_crew("9000000010", "Ravi")
    sunil = make_crew("9000000011", "Sunil")
    _, (job,) = new_visit(assigned=ravi)
    r = crew_client.post(f"/v1/crew/manager/jobs/{job.id}/reassign", headers=signin(boss),
                         json={"crew_id": str(sunil.id)})
    assert r.status_code == 200, r.text
    (row,) = rows(db)
    assert row.action == "reassign" and row.entity_id == str(job.id)
    assert row.detail["crew_id"] == [str(ravi.id), str(sunil.id)]
