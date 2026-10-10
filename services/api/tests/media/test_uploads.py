"""Signed uploads: request, send, confirm (CRW-SVC-04 to CRW-SVC-06, CRW-SVC-10)."""
from datetime import timedelta

from app.media.service import MB
from app.platform.db import utcnow


def request(client, headers, job_id, **changes):
    body = {"job_id": job_id, "kind": "photo", "stage": "Before",
            "content_type": "image/jpeg", "size_bytes": 1000, **changes}
    return client.post("/v1/media/uploads", headers=headers, json=body)


def test_the_flow_returns_a_signed_url_and_confirms_the_file(
        crew_client, make_crew, signin, new_visit, store):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    headers = signin(ravi)

    r = request(crew_client, headers, str(job.id))
    assert r.status_code == 201
    ticket = r.json()
    assert ticket["method"] == "PUT"
    assert ticket["headers"]["Content-Type"] == "image/jpeg"
    assert "sig=" in ticket["upload_url"]

    # Not there yet.
    early = crew_client.post(f"/v1/media/uploads/{ticket['id']}/confirm", headers=headers)
    assert early.status_code == 409 and early.json()["code"] == "upload_missing"

    sent = crew_client.put(ticket["upload_url"], content=b"p" * 1000)
    assert sent.status_code == 204
    done = crew_client.post(f"/v1/media/uploads/{ticket['id']}/confirm", headers=headers)
    assert done.json() == {"id": ticket["id"], "status": "confirmed", "size_bytes": 1000}
    # Confirming again is harmless: the phone may retry.
    again = crew_client.post(f"/v1/media/uploads/{ticket['id']}/confirm", headers=headers)
    assert again.status_code == 200


def test_formats_and_sizes_follow_rule_17(crew_client, make_crew, signin, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    headers = signin(ravi)
    jid = str(job.id)

    assert request(crew_client, headers, jid, content_type="image/heic").status_code == 201
    assert request(crew_client, headers, jid, kind="video",
                   content_type="video/quicktime", size_bytes=24 * MB).status_code == 201
    pdf = request(crew_client, headers, jid, content_type="application/pdf")
    assert pdf.status_code == 422 and "content_type" in pdf.json()["fields"]
    big_photo = request(crew_client, headers, jid, size_bytes=10 * MB + 1)
    assert big_photo.status_code == 422 and "size_bytes" in big_photo.json()["fields"]
    big_video = request(crew_client, headers, jid, kind="video", content_type="video/mp4",
                        size_bytes=25 * MB + 1)
    assert big_video.status_code == 422
    assert request(crew_client, headers, jid, stage="Later").status_code == 422
    assert request(crew_client, headers, jid, size_bytes=0).status_code == 422


def test_a_crew_member_cannot_upload_to_a_job_that_is_not_theirs(
        crew_client, make_crew, signin, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    sunil = make_crew("9000000011", "Sunil")
    _, (job,) = new_visit(assigned=ravi)
    assert request(crew_client, signin(sunil), str(job.id)).status_code == 404


def test_the_signed_url_cannot_be_forged_or_replayed(
        crew_client, make_crew, signin, new_visit, store):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    headers = signin(ravi)
    ticket = request(crew_client, headers, str(job.id)).json()

    forged = ticket["upload_url"].replace("sig=", "sig=00")
    assert crew_client.put(forged, content=b"x").status_code == 403
    expired = store.presign_upload(ticket["id"], "k", "image/jpeg",
                                   utcnow() - timedelta(minutes=1)).url
    assert crew_client.put(expired, content=b"x").status_code == 403

    assert crew_client.put(ticket["upload_url"], content=b"x" * 10).status_code == 204
    crew_client.post(f"/v1/media/uploads/{ticket['id']}/confirm", headers=headers)
    # Once confirmed, the file cannot be replaced.
    assert crew_client.put(ticket["upload_url"], content=b"y").status_code == 404


def test_an_oversized_body_is_refused(crew_client, make_crew, signin, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    ticket = request(crew_client, signin(ravi), str(job.id)).json()
    r = crew_client.put(ticket["upload_url"], content=b"x" * (10 * MB + 1))
    assert r.status_code == 422


def test_another_crew_member_cannot_confirm_my_upload(
        crew_client, make_crew, signin, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    sunil = make_crew("9000000011", "Sunil")
    _, (job,) = new_visit(assigned=ravi)
    ticket = request(crew_client, signin(ravi), str(job.id)).json()
    r = crew_client.post(f"/v1/media/uploads/{ticket['id']}/confirm", headers=signin(sunil))
    assert r.status_code == 404
