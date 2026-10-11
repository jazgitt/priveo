"""The crew member's cards and the work on a job (CRW-SCH, CRW-SVC, CRW-CNC)."""
import json

from sqlalchemy import select

from app.directory.models import ChecklistItem, CncReason, DirectoryService
from app.directory.seed import seed_defaults
from app.scheduling.models import Visit
from tests.visits.conftest import DAY, upload_file


def tick_all(client, headers, job_id):
    detail = client.get(f"/v1/crew/jobs/{job_id}", headers=headers).json()
    for item in detail["checklist"]:
        r = client.put(f"/v1/crew/jobs/{job_id}/checklist/{item['id']}", headers=headers,
                       json={"checked": True})
        assert r.status_code == 200, r.text


def test_cards_for_a_day_show_the_vehicle_and_never_the_customer(
        crew_client, make_crew, signin, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    new_visit(["Cleaning-External", "Cleaning-Internal"], assigned=ravi)
    new_visit(vehicle=1, assigned=ravi, day=DAY.replace(day=8))
    headers = signin(ravi)

    r = crew_client.get(f"/v1/crew/visits?date={DAY.isoformat()}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert (body["total"], body["done"], body["left"]) == (2, 0, 2)
    assert body["society"] == "Green Meadows"
    card = body["jobs"][0]
    assert card["vehicle"]["registration"] == "MH12AB1234"
    assert card["parking"] == "B2-14"
    assert card["start_time"] == "07:00"
    assert card["finish_by"] == "07:30"
    assert card["checklist_total"] == 5
    assert {c["service"] for c in body["jobs"]} == {"Cleaning-External", "Cleaning-Internal"}
    # CRW-SCH-13
    text = json.dumps(body)
    for secret in ("Secret", "Name", "9123456789", "owner@priveo.test", "A-101"):
        assert secret not in text

    everything = crew_client.get("/v1/crew/visits?all=true", headers=headers).json()
    assert everything["total"] == 3 and everything["date"] is None


def test_a_member_sees_only_their_own_jobs(crew_client, make_crew, signin, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    sunil = make_crew("9000000011", "Sunil")
    _, (job,) = new_visit(assigned=ravi)
    new_visit(vehicle=1, assigned=sunil)

    r = crew_client.get(f"/v1/crew/visits?date={DAY.isoformat()}", headers=signin(sunil))
    assert [c["vehicle"]["registration"] for c in r.json()["jobs"]] == ["MH12CD5678"]
    assert crew_client.get(f"/v1/crew/jobs/{job.id}", headers=signin(sunil)).status_code == 404


def test_a_trainee_sees_and_does_the_paired_members_jobs(
        crew_client, make_crew, signin, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    asha = make_crew("9000000012", "Asha", role="Trainee", member=ravi)
    _, (job,) = new_visit(assigned=ravi)

    headers = signin(asha)
    r = crew_client.get(f"/v1/crew/visits?date={DAY.isoformat()}", headers=headers)
    assert r.json()["total"] == 1
    item = crew_client.get(f"/v1/crew/jobs/{job.id}", headers=headers).json()["checklist"][0]
    ticked = crew_client.put(f"/v1/crew/jobs/{job.id}/checklist/{item['id']}",
                             headers=headers, json={"checked": True})
    assert ticked.status_code == 200
    # The Member sees the Trainee's tick (CRW-SCH-12).
    seen = crew_client.get(f"/v1/crew/jobs/{job.id}", headers=signin(ravi)).json()
    assert seen["checklist"][0]["checked_at"] is not None


def test_start_moves_a_job_to_in_progress(crew_client, make_crew, signin, new_visit, db):
    ravi = make_crew("9000000010", "Ravi")
    visit, (job,) = new_visit(assigned=ravi)
    headers = signin(ravi)

    r = crew_client.post(f"/v1/crew/jobs/{job.id}/start", headers=headers)
    assert r.json()["job"]["status"] == "In progress"
    assert r.json()["started_at"] is not None
    again = crew_client.post(f"/v1/crew/jobs/{job.id}/start", headers=headers)
    assert again.status_code == 200
    assert db.scalar(select(Visit.status).where(Visit.id == visit.id)) == "In progress"


def test_a_job_cannot_complete_until_checklist_and_proof_are_done(
        crew_client, make_crew, signin, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    headers = signin(ravi)
    jid = str(job.id)

    blocked = crew_client.post(f"/v1/crew/jobs/{jid}/complete", headers=headers)
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "job_not_ready"
    assert len(blocked.json()["fields"]) == 3

    tick_all(crew_client, headers, jid)
    upload_file(crew_client, headers, jid, kind="photo", stage="Before")
    detail = crew_client.get(f"/v1/crew/jobs/{jid}", headers=headers).json()
    assert detail["can_complete"] is False
    assert detail["missing"] == ["1 more photo to upload", "1 more video to upload"]
    assert crew_client.post(f"/v1/crew/jobs/{jid}/complete",
                            headers=headers).status_code == 409

    upload_file(crew_client, headers, jid, kind="photo", stage="After")
    upload_file(crew_client, headers, jid, kind="video", stage="During")
    done = crew_client.post(f"/v1/crew/jobs/{jid}/complete", headers=headers)
    assert done.status_code == 200, done.text
    assert done.json()["job"]["status"] == "Completed"
    assert done.json()["finished_at"] is not None
    assert done.json()["job"]["visit_status"] == "Completed"


def test_an_unconfirmed_upload_blocks_completion(crew_client, make_crew, signin, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    headers = signin(ravi)
    jid = str(job.id)
    tick_all(crew_client, headers, jid)
    for kind, stage in (("photo", "Before"), ("photo", "After"), ("video", "During")):
        upload_file(crew_client, headers, jid, kind=kind, stage=stage)
    # A fourth file was asked for and never confirmed.
    r = crew_client.post("/v1/media/uploads", headers=headers, json={
        "job_id": jid, "kind": "photo", "stage": "During", "content_type": "image/jpeg",
        "size_bytes": 100})
    assert r.status_code == 201

    blocked = crew_client.post(f"/v1/crew/jobs/{jid}/complete", headers=headers)
    assert blocked.status_code == 409
    assert "1 upload not confirmed yet" in blocked.json()["fields"].values()

    ticket = r.json()
    crew_client.put(ticket["upload_url"], content=b"y" * 100, headers=ticket["headers"])
    crew_client.post(f"/v1/media/uploads/{ticket['id']}/confirm", headers=headers)
    assert crew_client.post(f"/v1/crew/jobs/{jid}/complete",
                            headers=headers).status_code == 200


def test_a_completed_job_cannot_be_changed(crew_client, make_crew, signin, new_visit, db):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    headers = signin(ravi)
    jid = str(job.id)
    tick_all(crew_client, headers, jid)
    for kind, stage in (("photo", "Before"), ("photo", "After"), ("video", "During")):
        upload_file(crew_client, headers, jid, kind=kind, stage=stage)
    crew_client.post(f"/v1/crew/jobs/{jid}/complete", headers=headers)

    item = crew_client.get(f"/v1/crew/jobs/{jid}", headers=headers).json()["checklist"][0]
    untick = crew_client.put(f"/v1/crew/jobs/{jid}/checklist/{item['id']}", headers=headers,
                             json={"checked": False})
    assert untick.status_code == 409 and untick.json()["code"] == "job_closed"
    body = {"reason_key": "other"}
    assert crew_client.post(f"/v1/crew/jobs/{jid}/could-not-complete", headers=headers,
                            json=body).status_code == 409


def test_a_visit_is_completed_only_when_all_its_jobs_are_done(
        crew_client, make_crew, signin, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    _, jobs = new_visit(["Cleaning-External", "Cleaning-Internal"], assigned=ravi)
    headers = signin(ravi)
    first = str(jobs[0].id)
    tick_all(crew_client, headers, first)
    for kind, stage in (("photo", "Before"), ("photo", "After"), ("video", "During")):
        upload_file(crew_client, headers, first, kind=kind, stage=stage)
    done = crew_client.post(f"/v1/crew/jobs/{first}/complete", headers=headers).json()
    assert done["job"]["visit_status"] == "In progress"

    r = crew_client.post(f"/v1/crew/jobs/{jobs[1].id}/could-not-complete", headers=headers,
                         json={"reason_key": "car_locked", "note": "Locked, no one around"})
    assert r.status_code == 200, r.text
    assert r.json()["job"]["status"] == "Could not complete"
    assert r.json()["outcome"]["reason_key"] == "car_locked"
    assert r.json()["job"]["visit_status"] == "Could not complete"


def test_could_not_complete_needs_a_listed_reason(crew_client, make_crew, signin, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    headers = signin(ravi)

    reasons = crew_client.get("/v1/crew/reasons", headers=headers).json()
    assert "other" in {r["key"] for r in reasons}
    bad = crew_client.post(f"/v1/crew/jobs/{job.id}/could-not-complete", headers=headers,
                           json={"reason_key": "tired"})
    assert bad.status_code == 422
    assert "reason_key" in bad.json()["fields"]


def test_could_not_complete_can_carry_a_confirmed_photo(
        crew_client, make_crew, signin, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    headers = signin(ravi)
    jid = str(job.id)

    unready = crew_client.post(f"/v1/crew/jobs/{jid}/could-not-complete", headers=headers,
                               json={"reason_key": "other", "upload_id": "nope"})
    assert unready.status_code == 422
    photo = upload_file(crew_client, headers, jid, purpose="reason", stage=None)
    r = crew_client.post(f"/v1/crew/jobs/{jid}/could-not-complete", headers=headers,
                         json={"reason_key": "other", "upload_id": photo})
    assert r.status_code == 200


def test_a_draft_schedule_is_not_shown_to_the_crew(
        crew_client, make_crew, signin, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi, status="Draft")
    headers = signin(ravi)
    day = crew_client.get(f"/v1/crew/visits?date={DAY.isoformat()}", headers=headers)
    assert day.json()["total"] == 0
    assert crew_client.get(f"/v1/crew/jobs/{job.id}", headers=headers).status_code == 404


def test_profile_photo_needs_a_confirmed_upload(crew_client, make_crew, signin):
    ravi = make_crew("9000000010", "Ravi Kumar")
    headers = signin(ravi)
    assert crew_client.get("/v1/crew/profile/photo", headers=headers).json() == {
        "upload_id": None, "url": None}

    unready = crew_client.put("/v1/crew/profile/photo", headers=headers,
                              json={"upload_id": "nope"})
    assert unready.status_code == 422
    r = crew_client.post("/v1/media/uploads", headers=headers, json={
        "purpose": "profile", "kind": "photo", "content_type": "image/heic",
        "size_bytes": 10})
    ticket = r.json()
    crew_client.put(ticket["upload_url"], content=b"z" * 10, headers=ticket["headers"])
    crew_client.post(f"/v1/media/uploads/{ticket['id']}/confirm", headers=headers)
    saved = crew_client.put("/v1/crew/profile/photo", headers=headers,
                            json={"upload_id": ticket["id"]})
    assert saved.json()["upload_id"] == ticket["id"]


def test_only_crew_can_use_the_crew_routes(crew_client):
    assert crew_client.get("/v1/crew/visits").status_code == 401


# ---- the admin's checklists and reasons are honoured (ADM-CHK, ADM-CNC) -------------

def test_a_switched_off_checklist_item_and_reason_follow_the_admin(
        crew_client, make_crew, signin, new_visit, db):
    seed_defaults(db)
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    headers = signin(ravi)
    before = crew_client.get(f"/v1/crew/jobs/{job.id}", headers=headers).json()
    assert "glass" in {i["id"] for i in before["checklist"]}

    item = db.scalar(select(ChecklistItem).where(
        ChecklistItem.service == job.service, ChecklistItem.key == "glass"))
    item.active = False
    reason = db.scalar(select(CncReason).where(CncReason.key == "bad_weather"))
    reason.active = False
    db.commit()

    after = crew_client.get(f"/v1/crew/jobs/{job.id}", headers=headers).json()
    assert "glass" not in {i["id"] for i in after["checklist"]}
    assert len(after["checklist"]) == len(before["checklist"]) - 1
    reasons = {r["key"] for r in crew_client.get("/v1/crew/reasons", headers=headers).json()}
    assert "bad_weather" not in reasons and "other" in reasons
    gone = crew_client.post(f"/v1/crew/jobs/{job.id}/could-not-complete", headers=headers,
                            json={"reason_key": "bad_weather"})
    assert gone.status_code == 422


def test_a_changed_proof_minimum_is_the_one_required(
        crew_client, make_crew, signin, new_visit, db):
    seed_defaults(db)
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    headers = signin(ravi)
    row = db.scalar(select(DirectoryService).where(DirectoryService.name == job.service))
    row.min_photos, row.min_videos = 3, 0
    db.commit()
    req = crew_client.get(f"/v1/crew/jobs/{job.id}", headers=headers).json()["requirements"]
    assert (req["photos_required"], req["videos_required"]) == (3, 0)
