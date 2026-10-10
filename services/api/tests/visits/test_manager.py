"""CRW-MGR: a Manager sees the society's schedule and acts on other jobs."""
from app.directory.models import Society
from tests.visits.conftest import DAY


def test_a_member_cannot_use_manager_routes(crew_client, make_crew, signin, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    headers = signin(ravi)
    assert crew_client.get("/v1/crew/manager/schedule", headers=headers).status_code == 403
    assert crew_client.post(f"/v1/crew/manager/jobs/{job.id}/skip",
                            headers=headers).status_code == 403


def test_schedule_groups_the_societys_jobs_by_crew_member(
        crew_client, make_crew, signin, new_visit):
    boss = make_crew("9000000001", "Manju", role="Manager")
    ravi = make_crew("9000000010", "Ravi")
    make_crew("9000000011", "Sunil")
    new_visit(assigned=ravi)
    new_visit(vehicle=1)  # on nobody yet

    r = crew_client.get(f"/v1/crew/manager/schedule?date={DAY.isoformat()}",
                        headers=signin(boss))
    assert r.status_code == 200
    body = r.json()
    by_name = {c["name"]: c for c in body["crew"]}
    assert set(by_name) == {"Manju", "Ravi", "Sunil"}
    assert len(by_name["Ravi"]["jobs"]) == 1
    assert by_name["Sunil"]["jobs"] == []
    assert len(body["unassigned"]) == 1
    assert "9123456789" not in r.text and "Secret" not in r.text


def test_a_manager_marks_another_crews_job_could_not_complete(
        crew_client, make_crew, signin, new_visit):
    boss = make_crew("9000000001", "Manju", role="Manager")
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    r = crew_client.post(f"/v1/crew/manager/jobs/{job.id}/could-not-complete",
                         headers=signin(boss), json={"reason_key": "bad_weather"})
    assert r.status_code == 200
    assert r.json()["job"]["status"] == "Could not complete"
    # Ravi sees it closed too.
    seen = crew_client.get(f"/v1/crew/jobs/{job.id}", headers=signin(ravi)).json()
    assert seen["job"]["status"] == "Could not complete"


def test_a_manager_can_skip_a_job_and_the_visit_completes(
        crew_client, make_crew, signin, new_visit):
    boss = make_crew("9000000001", "Manju", role="Manager")
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    r = crew_client.post(f"/v1/crew/manager/jobs/{job.id}/skip", headers=signin(boss))
    assert r.json()["job"]["status"] == "Skipped"
    assert r.json()["outcome"]["kind"] == "skipped"
    assert r.json()["job"]["visit_status"] == "Skipped"
    again = crew_client.post(f"/v1/crew/manager/jobs/{job.id}/skip", headers=signin(boss))
    assert again.status_code == 409


def test_reassign_moves_the_job_and_follows_the_trainee(
        crew_client, make_crew, signin, new_visit):
    boss = make_crew("9000000001", "Manju", role="Manager")
    ravi = make_crew("9000000010", "Ravi")
    sunil = make_crew("9000000011", "Sunil")
    trainee = make_crew("9000000012", "Asha", role="Trainee", member=sunil)
    _, (job,) = new_visit(assigned=ravi)

    options = crew_client.get("/v1/crew/manager/crew", headers=signin(boss)).json()
    assert {o["name"] for o in options} == {"Manju", "Ravi", "Sunil"}

    # Not to a Trainee.
    bad = crew_client.post(f"/v1/crew/manager/jobs/{job.id}/reassign", headers=signin(boss),
                           json={"crew_id": str(trainee.id)})
    assert bad.status_code == 422
    r = crew_client.post(f"/v1/crew/manager/jobs/{job.id}/reassign", headers=signin(boss),
                         json={"crew_id": str(sunil.id)})
    assert r.status_code == 200
    assert r.json()["job"]["assigned_to"]["name"] == "Sunil"
    day = f"/v1/crew/visits?date={DAY.isoformat()}"
    assert crew_client.get(day, headers=signin(ravi)).json()["total"] == 0
    assert crew_client.get(day, headers=signin(sunil)).json()["total"] == 1
    assert crew_client.get(day, headers=signin(trainee)).json()["total"] == 1


def test_a_manager_cannot_reach_another_societys_job(
        crew_client, make_crew, signin, new_visit, db):
    other = Society(name="Other Society")
    db.add(other)
    db.commit()
    stranger = make_crew("9000000020", "Elsewhere", role="Manager", society=other)
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)

    headers = signin(stranger)
    assert crew_client.post(f"/v1/crew/manager/jobs/{job.id}/skip",
                            headers=headers).status_code == 404
    body = crew_client.get(f"/v1/crew/manager/schedule?date={DAY.isoformat()}",
                           headers=headers).json()
    assert all(c["jobs"] == [] for c in body["crew"])
