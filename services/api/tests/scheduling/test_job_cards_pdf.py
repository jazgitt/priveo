"""Job cards as PDF (P1-2): one PDF for all crew, and one PDF per crew.

Each option returns a PDF. Each crew starts on its own page, so the all-crew PDF has
one page per crew and the same pages as the per-crew PDFs put together."""
import io
import re
import uuid
from datetime import date

from pypdf import PdfReader

from app.directory import lookup
from app.directory.models import DirectoryService
from app.directory.seed import seed_defaults
from tests.scheduling.conftest import SUNDAY

BASE = "/v1/admin/scheduling"
CARDS = f"{BASE}/job-cards"


def pin_cleaning_to_20(world):
    """Short cleans, so two crew members take six cars a day."""
    seed_defaults(world.db)
    world.db.query(DirectoryService).filter(
        DirectoryService.name.in_(("Cleaning-External", "Cleaning-Internal"))
    ).update({"duration_minutes": 20})
    world.db.flush()
    lookup.invalidate()


def placed_day(world, api, admin, run_week):
    """A one-day draft with cards for two named crew members. Returns (schedule_id, crew ids)."""
    pin_cleaning_to_20(world)
    world.add_crew(name="Ravi")
    world.add_crew(name="Meena")
    for _ in range(8):
        world.add_vehicle(cutoff=None)
    world.db.commit()
    summary = run_week(days=1)
    board = api.get(f"{BASE}/board", headers=admin, params={"schedule_id": summary["schedule_id"]}).json()
    crews = sorted({j["crew_id"] for j in board["jobs"] if j["crew_id"]})
    assert len(crews) == 2
    return summary["schedule_id"], crews


def pages_of(response):
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    return PdfReader(io.BytesIO(response.content)).pages


def text_of(pages) -> str:
    return "\n".join(page.extract_text() for page in pages)


def has_image(page) -> bool:
    if "/XObject" not in page["/Resources"]:
        return False
    xobjects = page["/Resources"]["/XObject"].get_object()
    return any(xobjects[name].get_object().get("/Subtype") == "/Image" for name in xobjects)


def all_crew(api, admin, schedule_id):
    return api.get(f"{CARDS}/pdf", headers=admin,
                   params={"schedule_id": schedule_id, "date": SUNDAY.isoformat()})


def one_crew(api, admin, schedule_id, crew_id):
    return api.get(f"{CARDS}/crews/{crew_id}/pdf", headers=admin,
                   params={"schedule_id": schedule_id, "date": SUNDAY.isoformat()})


def test_all_crew_in_one_pdf_has_a_page_per_crew_and_matches_the_per_crew_pdfs(
    world, api, admin, run_week
):
    schedule_id, crews = placed_day(world, api, admin, run_week)

    response = all_crew(api, admin, schedule_id)
    everyone = pages_of(response)
    assert response.headers["content-disposition"] == f'attachment; filename="job-cards-{SUNDAY.isoformat()}.pdf"'
    assert len(everyone) == len(crews) == 2

    per_crew = [pages_of(one_crew(api, admin, schedule_id, crew_id)) for crew_id in crews]
    assert [len(p) for p in per_crew] == [1, 1]
    assert sum(len(p) for p in per_crew) == len(everyone)


def test_each_crew_pdf_holds_only_that_crew(world, api, admin, run_week):
    schedule_id, crews = placed_day(world, api, admin, run_week)

    names = []
    for crew_id in crews:
        text = text_of(pages_of(one_crew(api, admin, schedule_id, crew_id)))
        names.append(text)
    assert ("Ravi" in names[0]) != ("Ravi" in names[1])
    assert ("Meena" in names[0]) != ("Meena" in names[1])


def test_the_pdf_shows_logo_run_date_and_card_fields(world, api, admin, run_week):
    schedule_id, _ = placed_day(world, api, admin, run_week)

    pages = pages_of(all_crew(api, admin, schedule_id))
    text = text_of(pages)
    assert "Job cards" in text
    assert "18-Oct-26" in text  # the run date, dd-Mon-yy
    assert "Creta" in text  # the car model
    assert "Asha" in text  # the customer
    assert "Hyundai" not in text  # the make is not on the card (P2-7)
    assert has_image(pages[0])  # the logo


def test_unknown_crew_and_a_day_outside_the_schedule_are_refused(world, api, admin, run_week):
    schedule_id, _ = placed_day(world, api, admin, run_week)

    unknown = api.get(f"{CARDS}/crews/{uuid.uuid4()}/pdf", headers=admin,
                      params={"schedule_id": schedule_id, "date": SUNDAY.isoformat()})
    assert unknown.status_code == 404

    outside = api.get(f"{CARDS}/pdf", headers=admin,
                      params={"schedule_id": schedule_id, "date": date(2026, 11, 30).isoformat()})
    assert outside.status_code == 422


def test_sr_column_restarts_per_crew_and_special_notes_replace_status_and_notes(
    world, api, admin, run_week
):
    schedule_id, crews = placed_day(world, api, admin, run_week)
    for vehicle in world.vehicles:
        vehicle.notes = "Gate code 4321"
    world.db.commit()

    pages = pages_of(all_crew(api, admin, schedule_id))
    text = text_of(pages)
    assert "Sr #" in text
    assert "Special notes" in text
    assert "Status and notes" not in text
    assert "Gate code 4321" in text
    for status_text in ("Scheduled", "Late", "By hand", "Outside zone"):
        assert status_text not in text
    # Numbering starts at 1 on each crew's page.
    assert len(pages) == 2
    for page in pages:
        assert re.search(r"^1\s", page.extract_text(), re.MULTILINE)
