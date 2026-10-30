import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crew.models import CrewMember
from app.directory import defaults, lookup
from app.directory.models import (
    AddonCatalogueItem,
    ChecklistItem,
    CncReason,
    DirectoryAudit,
    DirectoryService,
    Plan,
    Society,
    SystemSetting,
    VehicleCatalogueEntry,
    WorkingSlot,
)
from app.directory.seed import seed_defaults
from app.identity.models import Login

BASE = "/v1/admin/directory"


def test_samples_have_five_steps(client, admin, seeded):
    lists = client.get(f'{BASE}/checklists', headers=admin).json()
    for entry in lists:
        assert len([item for item in entry['items'] if item['active']]) == 5


def test_invoice_seller_values_are_editable_and_the_seed_keeps_them(client, admin, engine):
    with Session(engine) as db:
        seed_defaults(db)
    edited = client.put(f'{BASE}/settings/invoice.seller_name', headers=admin,
                        json={'value': 'Priveo Services Pvt Ltd'})
    assert edited.status_code == 200 and edited.json()['value'] == 'Priveo Services Pvt Ltd'
    bad = client.put(f'{BASE}/settings/invoice.seller_gstin', headers=admin, json={'value': 'nope'})
    assert bad.status_code == 422
    good = client.put(f'{BASE}/settings/invoice.seller_gstin', headers=admin,
                      json={'value': '29ABCDE1234F1Z5'})
    assert good.status_code == 200
    with Session(engine) as db:
        seed_defaults(db)  # A deploy must not put the placeholder back.
        assert db.get(SystemSetting, 'invoice.seller_name').value == 'Priveo Services Pvt Ltd'
        assert db.get(SystemSetting, 'invoice.seller_gstin').value == '29ABCDE1234F1Z5'
        # An empty value is filled in again from configuration.
        db.get(SystemSetting, 'invoice.seller_address').value = ''
        db.commit()
        seed_defaults(db)
        assert db.get(SystemSetting, 'invoice.seller_address').value


@pytest.fixture
def seeded(engine, client):
    with Session(engine) as db:
        seed_defaults(db)


def society(client, admin, name="Green Park", **extra):
    r = client.post(f"{BASE}/societies", headers=admin, json={"name": name, **extra})
    assert r.status_code == 201, r.text
    return r.json()


# ---- auth ------------------------------------------------------------------------

ADMIN_PATHS = ["/societies", "/plans", "/vehicle-catalogue", "/services", "/checklists",
               "/reasons", "/settings", "/addons", "/audit"]


@pytest.mark.parametrize("path", ADMIN_PATHS)
def test_admin_endpoints_need_the_admin_role(client, customer, crew, path):
    assert client.get(BASE + path).status_code == 401
    assert client.get(BASE + path, headers=customer).status_code == 403
    assert client.get(BASE + path, headers=crew).status_code == 403


def test_writes_need_the_admin_role(client, customer):
    r = client.post(f"{BASE}/societies", headers=customer, json={"name": "X"})
    assert r.status_code == 403
    assert client.put(f"{BASE}/settings/support.hours", headers=customer,
                      json={"value": "x"}).status_code == 403


# ---- societies -------------------------------------------------------------------

def test_society_create_list_update(client, admin, engine):
    made = society(client, admin, sector="Sector 5", city="Pune")
    assert made["parking_basements"] == ["B1", "B2", "B3", "B4"]
    assert made["active"] and made["cars_serviced"] == 0
    # A new society starts with the default working slots (ADM-SVS-06).
    slots = client.get(f"{BASE}/societies/{made['id']}/slots", headers=admin).json()
    assert {s["service"] for s in slots} == set(defaults.SERVICES)
    external = next(s for s in slots if s["service"] == "Cleaning-External")
    assert (external["start"], external["end"]) == ("05:00", "11:00")
    assert len(external["days"]) == 7
    spa = next(s for s in slots if s["service"] == "Deep Spa")
    assert (spa["start"], spa["end"]) == ("00:00", "24:00")

    r = client.patch(f"{BASE}/societies/{made['id']}", headers=admin,
                     json={"city": "Mumbai", "parking_basements": ["B1", "P1"]})
    assert r.status_code == 200
    assert r.json()["city"] == "Mumbai" and r.json()["parking_basements"] == ["B1", "P1"]
    names = [x["name"] for x in client.get(f"{BASE}/societies", headers=admin).json()]
    assert names == ["Green Park", "Priveo Demo Society"]


def test_society_validation(client, admin):
    society(client, admin)
    assert client.post(f"{BASE}/societies", headers=admin, json={"name": ""}).status_code == 422
    dup = client.post(f"{BASE}/societies", headers=admin, json={"name": "green park"})
    assert dup.status_code == 409 and dup.json()["code"] == "duplicate"
    bad = client.post(f"{BASE}/societies", headers=admin,
                      json={"name": "Other", "parking_basements": ["B1", "b1"]})
    assert bad.status_code == 422 and "parking_basements" in bad.json()["fields"]
    assert client.get(f"{BASE}/societies/{uuid.uuid4()}", headers=admin).status_code == 404


def test_society_deactivate_and_no_delete(client, admin, customer):
    made = society(client, admin)
    assert client.delete(f"{BASE}/societies/{made['id']}", headers=admin).status_code == 405
    r = client.post(f"{BASE}/societies/{made['id']}/deactivate", headers=admin)
    assert r.status_code == 200 and r.json()["active"] is False
    # The customer list shows only active societies (ADM-REF-01).
    names = [x["name"] for x in client.get("/v1/customer/directory/societies",
                                           headers=customer).json()]
    assert "Green Park" not in names
    assert client.post(f"{BASE}/societies/{made['id']}/reactivate",
                       headers=admin).json()["active"] is True
    names = [x["name"] for x in client.get("/v1/customer/directory/societies",
                                           headers=customer).json()]
    assert "Green Park" in names


def test_society_with_active_subscriptions_or_crew_cannot_be_deactivated(
        client, admin, engine):
    with Session(engine) as db:
        demo = db.scalar(select(Society).where(Society.name == "Priveo Demo Society"))
        demo_id = demo.id
    r = client.post(f"{BASE}/societies/{demo_id}/deactivate", headers=admin)
    assert r.status_code == 409 and r.json()["code"] == "in_use"
    got = client.get(f"{BASE}/societies/{demo_id}", headers=admin).json()
    assert got["active_subscriptions"] == 2 and got["cars_serviced"] == 2

    made = society(client, admin, name="Crew Only")
    with Session(engine) as db:
        login = Login(role="crew", login_id="9111111111", display_name="Ravi")
        db.add(login)
        db.flush()
        db.add(CrewMember(login_id=login.id, name="Ravi", mobile="9111111111",
                          society_id=uuid.UUID(made["id"]), role="Member", working_hours=[]))
        db.commit()
    r = client.post(f"{BASE}/societies/{made['id']}/deactivate", headers=admin)
    assert r.status_code == 409 and r.json()["fields"]["active_crew"] == "1"
    with Session(engine) as db:
        db.get(Login, db.scalar(select(Login.id).where(Login.login_id == "9111111111"))
               ).active = False
        db.commit()
    assert client.post(f"{BASE}/societies/{made['id']}/deactivate",
                       headers=admin).status_code == 200


# ---- working slots ---------------------------------------------------------------

def test_slots_crud_and_rules(client, admin):
    made = society(client, admin)
    url = f"{BASE}/societies/{made['id']}/slots"
    r = client.post(url, headers=admin, json={
        "service": "Cleaning-External", "start": "16:00", "end": "18:00",
        "days": ["Monday", "Tuesday"]})
    assert r.status_code == 201, r.text
    slot = r.json()
    assert slot["days"] == ["Monday", "Tuesday"] and slot["start"] == "16:00"

    # The end must be after the start (ADM-SVS-07).
    bad = client.post(url, headers=admin, json={
        "service": "Deep Spa", "start": "10:00", "end": "09:00", "days": ["Monday"]})
    assert bad.status_code == 422 and "end" in bad.json()["fields"]
    # Two slots of a service cannot overlap on a day (ADM-SVS-07).
    clash = client.post(url, headers=admin, json={
        "service": "Cleaning-External", "start": "10:00", "end": "12:00",
        "days": ["Wednesday", "Monday"]})
    assert clash.status_code == 409 and clash.json()["code"] == "overlap"
    # No clash on a day the other slot does not use, or on another service.
    assert client.post(url, headers=admin, json={
        "service": "Cleaning-External", "start": "16:00", "end": "18:00",
        "days": ["Friday"]}).status_code == 201
    assert client.post(url, headers=admin, json={
        "service": "Cleaning-Internal", "start": "16:00", "end": "18:00",
        "days": ["Monday"]}).status_code == 201
    for payload in ({"service": "Window", "start": "10:00", "end": "11:00", "days": ["Monday"]},
                    {"service": "Deep Spa", "start": "25:00", "end": "26:00",
                     "days": ["Monday"]},
                    {"service": "Deep Spa", "start": "10:00", "end": "11:00",
                     "days": ["Funday"]}):
        assert client.post(url, headers=admin, json=payload).status_code == 422

    up = client.patch(f"{BASE}/slots/{slot['id']}", headers=admin, json={"end": "19:30"})
    assert up.status_code == 200 and up.json()["end"] == "19:30"
    clash = client.patch(f"{BASE}/slots/{slot['id']}", headers=admin, json={"start": "06:00"})
    assert clash.status_code == 409

    # Slots can be deleted (ADM-SVS-04).
    assert client.delete(f"{BASE}/slots/{slot['id']}", headers=admin).status_code == 204
    assert client.delete(f"{BASE}/slots/{slot['id']}", headers=admin).status_code == 404
    assert client.get(f"{BASE}/societies/{uuid.uuid4()}/slots",
                      headers=admin).status_code == 404


def test_slots_of_a_society_are_independent(client, admin):
    a, b = society(client, admin, "A"), society(client, admin, "B")
    one = client.get(f"{BASE}/societies/{a['id']}/slots?service=Deep Spa", headers=admin).json()
    assert len(one) == 1
    client.delete(f"{BASE}/slots/{one[0]['id']}", headers=admin)
    assert len(client.get(f"{BASE}/societies/{a['id']}/slots", headers=admin).json()) == 2
    assert len(client.get(f"{BASE}/societies/{b['id']}/slots", headers=admin).json()) == 3


# ---- plans -----------------------------------------------------------------------

def test_plans(client, admin, customer):
    r = client.post(f"{BASE}/plans", headers=admin, json={
        "name": "Basic", "monthly_price_rupees": 599, "list_price_rupees": 799,
        "includes_interior": False, "inclusions": ["Exterior 7 days"]})
    assert r.status_code == 201, r.text
    plan = r.json()
    assert plan["active"] and plan["active_subscriptions"] == 0
    assert plan["code"] == "PLN-0001"  # A unique plan ID, never reused.
    second = client.post(f"{BASE}/plans", headers=admin, json={
        "name": "Second", "monthly_price_rupees": 700}).json()
    assert second["code"] == "PLN-0002"
    client.post(f"{BASE}/plans/{second['id']}/deactivate", headers=admin)

    assert client.post(f"{BASE}/plans", headers=admin, json={
        "name": "basic", "monthly_price_rupees": 1}).status_code == 409
    assert client.post(f"{BASE}/plans", headers=admin, json={
        "name": "Zero", "monthly_price_rupees": 0}).status_code == 422
    below = client.post(f"{BASE}/plans", headers=admin, json={
        "name": "Odd", "monthly_price_rupees": 900, "list_price_rupees": 800})
    assert below.status_code == 422 and "list_price_rupees" in below.json()["fields"]

    up = client.patch(f"{BASE}/plans/{plan['id']}", headers=admin,
                      json={"monthly_price_rupees": 649, "includes_interior": True})
    assert up.json()["code"] == "PLN-0001"  # An edit keeps the ID.
    assert up.json()["monthly_price_rupees"] == 649 and up.json()["includes_interior"]
    clear = client.patch(f"{BASE}/plans/{plan['id']}", headers=admin,
                         json={"clear_list_price": True})
    assert clear.json()["list_price_rupees"] is None
    assert client.patch(f"{BASE}/plans/{plan['id']}", headers=admin,
                        json={"list_price_rupees": 100}).status_code == 422

    offered = [p["name"] for p in client.get("/v1/customer/directory/plans",
                                             headers=customer).json()]
    assert offered == ["Basic"]
    assert client.delete(f"{BASE}/plans/{plan['id']}", headers=admin).status_code == 405
    off = client.post(f"{BASE}/plans/{plan['id']}/deactivate", headers=admin)
    assert off.json()["active"] is False
    assert client.get("/v1/customer/directory/plans", headers=customer).json() == []
    assert len(client.get(f"{BASE}/plans?include_inactive=false", headers=admin).json()) == 0
    assert len(client.get(f"{BASE}/plans", headers=admin).json()) == 2


def test_plan_vehicle_category_is_optional_and_must_exist(client, admin):
    client.post(f"{BASE}/vehicle-catalogue", headers=admin, json={
        "make": "Tata", "model": "Nexon", "variant": "", "category": "SUV"})
    plain = client.post(f"{BASE}/plans", headers=admin, json={
        "name": "Any car", "monthly_price_rupees": 500}).json()
    assert plain["vehicle_category"] is None

    linked = client.post(f"{BASE}/plans", headers=admin, json={
        "name": "SUV plan", "monthly_price_rupees": 900, "vehicle_category": "SUV"})
    assert linked.status_code == 201 and linked.json()["vehicle_category"] == "SUV"

    bad = client.post(f"{BASE}/plans", headers=admin, json={
        "name": "Boat plan", "monthly_price_rupees": 900, "vehicle_category": "Boat"})
    assert bad.status_code == 422 and "vehicle_category" in bad.json()["fields"]

    pid = plain["id"]
    set_it = client.patch(f"{BASE}/plans/{pid}", headers=admin, json={"vehicle_category": "SUV"})
    assert set_it.json()["vehicle_category"] == "SUV"
    kept = client.patch(f"{BASE}/plans/{pid}", headers=admin, json={"badge": "New"})
    assert kept.json()["vehicle_category"] == "SUV"
    cleared = client.patch(f"{BASE}/plans/{pid}", headers=admin,
                           json={"clear_vehicle_category": True})
    assert cleared.json()["vehicle_category"] is None
    assert client.get(f"{BASE}/plans", headers=admin).json()[0]["vehicle_category"] in (None, "SUV")


def test_plan_counts_subscriptions_on_it(client, admin, engine):
    from app.customers.models import Subscription
    plan = client.post(f"{BASE}/plans", headers=admin, json={
        "name": "Basic", "monthly_price_rupees": 599}).json()
    with Session(engine) as db:
        for sub in db.scalars(select(Subscription)):
            sub.plan_id = uuid.UUID(plan["id"])
        db.commit()
    # Deactivating is allowed: subscriptions on it continue (ADM-SET-01).
    r = client.post(f"{BASE}/plans/{plan['id']}/deactivate", headers=admin)
    assert r.status_code == 200 and r.json()["active_subscriptions"] == 2


# ---- vehicle catalogue -----------------------------------------------------------

def test_vehicle_catalogue(client, admin, customer):
    body = {"make": "Maruti Suzuki", "model": "Swift", "variant": "ZXi", "category": "Hatchback"}
    r = client.post(f"{BASE}/vehicle-catalogue", headers=admin, json=body)
    assert r.status_code == 201, r.text
    entry = r.json()
    assert client.post(f"{BASE}/vehicle-catalogue", headers=admin,
                       json={**body, "make": "maruti suzuki"}).status_code == 409
    assert client.post(f"{BASE}/vehicle-catalogue", headers=admin,
                       json={**body, "category": ""}).status_code == 422
    client.post(f"{BASE}/vehicle-catalogue", headers=admin,
                json={**body, "variant": "VXi", "category": "Hatchback"})
    client.post(f"{BASE}/vehicle-catalogue", headers=admin,
                json={"make": "Kia", "model": "Seltos", "variant": "HTK", "category": "SUV"})

    up = client.patch(f"{BASE}/vehicle-catalogue/{entry['id']}", headers=admin,
                      json={"category": "Compact"})
    assert up.json()["category"] == "Compact"
    assert client.patch(f"{BASE}/vehicle-catalogue/{entry['id']}", headers=admin,
                        json={"variant": "VXi"}).status_code == 409
    assert client.get(f"{BASE}/vehicle-catalogue?make=kia", headers=admin).json()[0][
        "model"] == "Seltos"
    assert client.get(f"{BASE}/vehicle-catalogue?q=swi", headers=admin).json()[0][
        "model"] == "Swift"
    assert client.get(f"{BASE}/vehicle-catalogue/categories",
                      headers=admin).json() == ["Compact", "Hatchback", "SUV"]

    off = client.post(f"{BASE}/vehicle-catalogue/{entry['id']}/deactivate", headers=admin)
    assert off.json()["active"] is False
    shown = client.get("/v1/customer/directory/vehicle-catalogue", headers=customer).json()
    assert {(e["model"], e["variant"]) for e in shown} == {("Swift", "VXi"),
                                                           ("Seltos", "HTK")}
    assert client.delete(f"{BASE}/vehicle-catalogue/{entry['id']}",
                         headers=admin).status_code == 405


def test_category_lookup(client, admin, db):
    client.post(f"{BASE}/vehicle-catalogue", headers=admin, json={
        "make": "Kia", "model": "Seltos", "variant": "HTK", "category": "SUV"})
    assert lookup.category_for(db, "kia", "seltos", "htk") == "SUV"
    assert lookup.category_for(db, "Kia", "Seltos", "other") == "SUV"
    assert lookup.category_for(db, "Kia", "Sonet") is None


# ---- services and checklists -----------------------------------------------------

def test_services_defaults_and_update(client, admin):
    rows = {s["name"]: s for s in client.get(f"{BASE}/services", headers=admin).json()}
    assert rows["Cleaning-External"]["duration_minutes"] == 20
    assert rows["Deep Spa"]["duration_minutes"] == 120
    assert rows["Deep Spa"]["min_photos"] == 2 and rows["Deep Spa"]["min_videos"] == 1

    r = client.patch(f"{BASE}/services/Deep Spa", headers=admin,
                     json={"duration_minutes": 150, "min_photos": 4, "min_videos": 0})
    assert r.status_code == 200
    assert r.json() == {"name": "Deep Spa", "duration_minutes": 150, "min_photos": 4,
                        "min_videos": 0}
    assert client.patch(f"{BASE}/services/Window", headers=admin,
                        json={"min_photos": 1}).status_code == 404
    assert client.patch(f"{BASE}/services/Deep Spa", headers=admin,
                        json={"duration_minutes": 1}).status_code == 422
    assert client.patch(f"{BASE}/services/Deep Spa", headers=admin,
                        json={"min_photos": -1}).status_code == 422


def test_checklist_items(client, admin, seeded):
    lst = client.get(f"{BASE}/checklists/Cleaning-External", headers=admin).json()
    assert [i["key"] for i in lst["items"]] == [
        "body", "glass", "wheels", "tyres", "inspection"]
    assert client.get(f"{BASE}/checklists/Window", headers=admin).status_code == 404
    assert len(client.get(f"{BASE}/checklists", headers=admin).json()) == 3

    r = client.post(f"{BASE}/checklists/Cleaning-External/items", headers=admin,
                    json={"label": "Mirrors wiped"})
    assert r.status_code == 201 and r.json()["key"] == "mirrors_wiped"
    again = client.post(f"{BASE}/checklists/Cleaning-External/items", headers=admin,
                        json={"label": "Mirrors  wiped!"})
    assert again.json()["key"] == "mirrors_wiped_2"
    assert client.post(f"{BASE}/checklists/Cleaning-External/items", headers=admin,
                       json={"label": "  "}).status_code == 422

    # Reorder.
    items = client.get(f"{BASE}/checklists/Cleaning-External", headers=admin).json()["items"]
    ids = [i["id"] for i in items][::-1]
    got = client.put(f"{BASE}/checklists/Cleaning-External/order", headers=admin,
                     json={"ids": ids}).json()
    assert [i["id"] for i in got["items"]] == ids
    bad = client.put(f"{BASE}/checklists/Cleaning-External/order", headers=admin,
                     json={"ids": ids[:2]})
    assert bad.status_code == 422

    # A rename keeps the old item readable on past visits (ADM-CHK-05).
    glass = next(i for i in items if i["key"] == "glass")
    renamed = client.patch(f"{BASE}/checklist-items/{glass['id']}", headers=admin,
                           json={"label": "Windows cleaned"}).json()
    assert renamed["replaced_id"] == glass["id"]
    assert renamed["item"]["label"] == "Windows cleaned" and renamed["item"]["active"]
    assert renamed["item"]["key"] != "glass"

    off = client.post(f"{BASE}/checklist-items/{renamed['item']['id']}/deactivate",
                      headers=admin)
    assert off.json()["active"] is False


def test_the_last_checklist_item_cannot_be_deactivated(client, admin, seeded):
    items = client.get(f"{BASE}/checklists/Deep Spa", headers=admin).json()["items"]
    for item in items[:-1]:
        assert client.post(f"{BASE}/checklist-items/{item['id']}/deactivate",
                           headers=admin).status_code == 200
    r = client.post(f"{BASE}/checklist-items/{items[-1]['id']}/deactivate", headers=admin)
    assert r.status_code == 409


def test_checklist_lookup_is_active_items_in_order(client, admin, seeded, db):
    entries = lookup.checklist_for(db, "Cleaning-Internal")
    assert [(e.key, e.label) for e in entries] == list(defaults.CHECKLISTS["Cleaning-Internal"])
    items = client.get(f"{BASE}/checklists/Cleaning-Internal", headers=admin).json()["items"]
    client.post(f"{BASE}/checklist-items/{items[0]['id']}/deactivate", headers=admin)
    db.expire_all()
    keys = [e.key for e in lookup.checklist_for(db, "Cleaning-Internal")]
    assert items[0]["key"] not in keys
    # Still readable by key for a visit already done.
    assert lookup.checklist_label(db, "Cleaning-Internal", items[0]["key"]) == items[0]["label"]


def test_lookups_fall_back_to_the_old_constants_before_the_seed(db):
    assert [(e.key, e.label) for e in lookup.checklist_for(db, "Deep Spa")] == list(
        defaults.CHECKLISTS["Deep Spa"])
    assert [(r.key, r.label) for r in lookup.reasons(db)] == list(defaults.REASONS)
    assert lookup.proof_minimums(db, "Deep Spa") == (2, 1)
    assert lookup.duration_minutes(db, "Deep Spa") == 120
    assert lookup.setting(db, "schedule.unfreeze_code") == "unfreeze"
    assert lookup.addon_price(db) == (1500, 2000)


# ---- reasons ---------------------------------------------------------------------

def test_reasons(client, admin, crew, seeded, db):
    rows = client.get(f"{BASE}/reasons", headers=admin).json()
    assert [r["key"] for r in rows][:2] == ["car_not_in_spot", "car_locked"]
    new = client.post(f"{BASE}/reasons", headers=admin, json={"label": "Gate closed"})
    assert new.status_code == 201 and new.json()["key"] == "gate_closed"
    assert client.post(f"{BASE}/reasons", headers=admin,
                       json={"label": "gate CLOSED"}).status_code == 409
    assert client.post(f"{BASE}/reasons", headers=admin,
                       json={"label": ""}).status_code == 422

    renamed = client.patch(f"{BASE}/reasons/{new.json()['id']}", headers=admin,
                           json={"label": "Society gate closed"})
    assert renamed.json()["label"] == "Society gate closed"
    assert renamed.json()["key"] == "gate_closed"

    ids = [r["id"] for r in client.get(f"{BASE}/reasons", headers=admin).json()][::-1]
    reordered = client.put(f"{BASE}/reasons/order", headers=admin, json={"ids": ids}).json()
    assert [r["id"] for r in reordered] == ids
    assert client.put(f"{BASE}/reasons/order", headers=admin,
                      json={"ids": ids[1:]}).status_code == 422

    off = next(r for r in reordered if r["key"] == "bad_weather")
    assert client.post(f"{BASE}/reasons/{off['id']}/deactivate",
                       headers=admin).json()["active"] is False
    db.expire_all()
    keys = [r.key for r in lookup.reasons(db)]
    assert "bad_weather" not in keys and keys[0] == "gate_closed"
    # Past records keep it.
    assert lookup.reason_label(db, "bad_weather") == "Bad weather"
    # The crew's own list is untouched until the visits module reads the lookup.
    assert client.get("/v1/crew/reasons", headers=crew).status_code == 200
    assert client.delete(f"{BASE}/reasons/{off['id']}", headers=admin).status_code == 405


def test_the_last_reason_cannot_be_deactivated(client, admin, seeded):
    rows = client.get(f"{BASE}/reasons", headers=admin).json()
    for row in rows[:-1]:
        assert client.post(f"{BASE}/reasons/{row['id']}/deactivate",
                           headers=admin).status_code == 200
    assert client.post(f"{BASE}/reasons/{rows[-1]['id']}/deactivate",
                       headers=admin).status_code == 409


# ---- settings --------------------------------------------------------------------

def test_settings_list_and_typed_values(client, admin, db):
    rows = {r["key"]: r for r in client.get(f"{BASE}/settings", headers=admin).json()}
    assert rows["schedule.unfreeze_code"]["value"] == "unfreeze"
    assert rows["schedule.unfreeze_code"]["is_default"] is True
    assert rows["billing.inactive_after_days"]["value"] == 7
    assert rows["billing.inactive_after_days"]["kind"] == "int"
    assert rows["schedule.freeze_hour"]["value"] == 20
    assert rows["schedule.customer_change_hour"]["value"] == 21

    r = client.put(f"{BASE}/settings/support.helpline", headers=admin,
                   json={"value": "+91 98765 43210"})
    assert r.status_code == 200, r.text
    assert r.json()["value"] == "+919876543210" and r.json()["is_default"] is False
    assert r.json()["updated_by"] is not None
    assert lookup.setting(db, "support.helpline") == "+919876543210"


@pytest.mark.parametrize("key,value", [
    ("support.helpline", "abc"),
    ("support.whatsapp", "12345"),
    ("payment.upi_id", "no-at-sign"),
    ("payment.upi_qr_url", "ftp://x"),
    ("billing.inactive_after_days", "seven"),
    ("billing.inactive_after_days", -1),
    ("schedule.freeze_hour", 24),
    ("schedule.default_cutoff_time", "25:00"),
    ("schedule.unfreeze_code", ""),
    ("support.hours", "x" * 200),
    ("support.hours", None),
])
def test_setting_validation(client, admin, key, value):
    r = client.put(f"{BASE}/settings/{key}", headers=admin, json={"value": value})
    assert r.status_code == 422, r.text
    assert "value" in r.json()["fields"]


def test_setting_accepts_valid_values(client, admin, db):
    ok = [("payment.upi_id", "priveo@okbank", "priveo@okbank"),
          ("payment.upi_qr_url", "", ""),
          ("payment.upi_qr_url", "https://x.test/qr.png", "https://x.test/qr.png"),
          ("billing.inactive_after_days", "10", 10),
          ("schedule.default_cutoff_time", "08:30", "08:30"),
          ("schedule.unfreeze_code", "open sesame", "open sesame")]
    for key, sent, stored in ok:
        r = client.put(f"{BASE}/settings/{key}", headers=admin, json={"value": sent})
        assert r.status_code == 200, (key, r.text)
        assert lookup.setting(db, key) == stored


def test_unknown_setting(client, admin):
    assert client.get(f"{BASE}/settings/nope", headers=admin).status_code == 404
    assert client.put(f"{BASE}/settings/nope", headers=admin,
                      json={"value": "x"}).status_code == 404


def test_patch_settings_is_all_or_nothing(client, admin, db):
    bad = client.patch(f"{BASE}/settings", headers=admin, json={"values": {
        "support.hours": "9 AM to 5 PM", "support.helpline": "abc", "nope": "x"}})
    assert bad.status_code == 422
    assert set(bad.json()["fields"]) == {"support.helpline", "nope"}
    assert lookup.setting(db, "support.hours") == "6 AM to 10 PM"
    ok = client.patch(f"{BASE}/settings", headers=admin, json={"values": {
        "support.hours": "9 AM to 5 PM", "billing.cycle_days": 28}})
    assert ok.status_code == 200 and len(ok.json()) == 2
    assert lookup.setting(db, "billing.cycle_days") == 28


def test_settings_cache(client, admin, engine, db):
    clock = {"now": 1000.0}
    lookup._clock = lambda: clock["now"]
    try:
        assert lookup.setting(db, "support.hours") == "6 AM to 10 PM"
        # A write behind the cache's back is not seen until it expires...
        with Session(engine) as other:
            other.add(SystemSetting(key="support.hours", value="7 AM to 9 PM"))
            other.commit()
        assert lookup.setting(db, "support.hours") == "6 AM to 10 PM"
        clock["now"] += lookup.CACHE_SECONDS + 1
        assert lookup.setting(db, "support.hours") == "7 AM to 9 PM"
        # ...a write through the API is seen at once.
        client.put(f"{BASE}/settings/support.hours", headers=admin, json={"value": "8 AM"})
        assert lookup.setting(db, "support.hours") == "8 AM"
        # Invalidate by hand.
        with Session(engine) as other:
            other.get(SystemSetting, "support.hours").value = "9 AM"
            other.commit()
        lookup.invalidate(db)
        assert lookup.setting(db, "support.hours") == "9 AM"
    finally:
        import time
        lookup._clock = time.monotonic


def test_settings_default_to_the_environment_configuration(monkeypatch, db):
    from app.billing.config import get_money_settings
    from app.support.config import get_support_settings
    monkeypatch.setenv("SUPPORT_HELPLINE", "+911111111111")
    monkeypatch.setenv("MONEY_UPI_ID", "env@upi")
    get_support_settings.cache_clear()
    get_money_settings.cache_clear()
    try:
        assert lookup.setting(db, "support.helpline") == "+911111111111"
        assert lookup.setting(db, "payment.upi_id") == "env@upi"
    finally:
        get_support_settings.cache_clear()
        get_money_settings.cache_clear()


# ---- add-on catalogue ------------------------------------------------------------

def test_addon_catalogue(client, admin, customer, db):
    r = client.post(f"{BASE}/addons", headers=admin, json={
        "name": "Deep Spa", "description": "Full spa", "service": "Deep Spa",
        "price_rupees": 1800, "list_price_rupees": 2200})
    assert r.status_code == 201, r.text
    addon = r.json()
    assert addon["duration_minutes"] == 120 and addon["active"]
    assert addon["code"].startswith("ADN-")
    db.expire_all()
    assert lookup.addon_price(db) == (1800, 2200)

    assert client.post(f"{BASE}/addons", headers=admin, json={
        "name": "deep spa", "price_rupees": 1}).status_code == 409
    assert client.post(f"{BASE}/addons", headers=admin, json={
        "name": "Wax", "service": "Waxing", "price_rupees": 1}).status_code == 422
    assert client.post(f"{BASE}/addons", headers=admin, json={
        "name": "Wax", "price_rupees": -1}).status_code == 422
    assert client.post(f"{BASE}/addons", headers=admin, json={
        "name": "Wax", "price_rupees": 500, "list_price_rupees": 400}).status_code == 422

    up = client.patch(f"{BASE}/addons/{addon['id']}", headers=admin,
                      json={"price_rupees": 1700, "duration_minutes": 130})
    assert up.json()["price_rupees"] == 1700 and up.json()["duration_minutes"] == 130
    db.expire_all()
    assert lookup.addon_price(db) == (1700, 2200)
    assert client.patch(f"{BASE}/addons/{addon['id']}", headers=admin,
                        json={"clear_list_price": True}).json()["list_price_rupees"] is None

    shown = client.get("/v1/customer/directory/addons", headers=customer).json()
    assert [a["name"] for a in shown] == ["Deep Spa"] and shown[0]["price_rupees"] == 1700
    assert client.post(f"{BASE}/addons/{addon['id']}/deactivate",
                       headers=admin).json()["active"] is False
    assert client.get("/v1/customer/directory/addons", headers=customer).json() == []
    assert client.delete(f"{BASE}/addons/{addon['id']}", headers=admin).status_code == 405


# ---- customer reads --------------------------------------------------------------

def test_customer_reads_need_a_customer(client, admin, crew):
    for path in ("societies", "plans", "vehicle-catalogue", "addons"):
        url = f"/v1/customer/directory/{path}"
        assert client.get(url).status_code == 401
        assert client.get(url, headers=admin).status_code == 403
        assert client.get(url, headers=crew).status_code == 403


# ---- audit -----------------------------------------------------------------------

def test_changes_are_audited_with_the_admin(client, admin, engine):
    made = society(client, admin)
    client.patch(f"{BASE}/societies/{made['id']}", headers=admin, json={"city": "Pune"})
    client.put(f"{BASE}/settings/support.hours", headers=admin, json={"value": "8 AM"})
    rows = client.get(f"{BASE}/audit", headers=admin).json()
    kinds = {(r["entity"], r["action"]) for r in rows}
    assert {("society", "create"), ("society", "update"), ("setting", "update")} <= kinds
    update = next(r for r in rows if r["entity"] == "society" and r["action"] == "update")
    assert update["detail"] == {"city": ["", "Pune"]}
    assert all(r["admin_login_id"] for r in rows)
    only = client.get(f"{BASE}/audit?entity=setting", headers=admin).json()
    assert {r["entity"] for r in only} == {"setting"}
    # A change that changes nothing is not audited.
    before = len(client.get(f"{BASE}/audit", headers=admin).json())
    client.patch(f"{BASE}/societies/{made['id']}", headers=admin, json={"city": "Pune"})
    assert len(client.get(f"{BASE}/audit", headers=admin).json()) == before
    with Session(engine) as db:
        assert db.scalar(select(DirectoryAudit).limit(1)) is not None


# ---- seed ------------------------------------------------------------------------

def test_seed_defaults_inserts_the_stated_defaults(engine, client, db):
    added = seed_defaults(db)
    assert added["services"] == 3 and added["reasons"] == len(defaults.REASONS) and added["plans"] == 1
    assert added["checklist_items"] == 5 + 4 + 6
    assert added["settings"] >= 15
    assert db.scalar(select(CncReason).where(CncReason.key == "other")) is not None
    assert lookup.setting(db, "schedule.unfreeze_code") == "unfreeze"
    assert lookup.addon_price(db) == (1500, 2000)
    assert lookup.durations(db) == defaults.DURATIONS
    # The demo society got the default slots.
    demo = db.scalar(select(Society).where(Society.name == "Priveo Demo Society"))
    assert len(lookup.working_slots(db, demo.id)) == 3


def test_seed_defaults_is_idempotent_and_keeps_admin_changes(client, admin, engine):
    with Session(engine) as db:
        seed_defaults(db)
    items = client.get(f"{BASE}/checklists/Cleaning-External", headers=admin).json()["items"]
    client.post(f"{BASE}/checklist-items/{items[0]['id']}/deactivate", headers=admin)
    client.put(f"{BASE}/settings/schedule.unfreeze_code", headers=admin,
               json={"value": "sesame"})
    reasons = client.get(f"{BASE}/reasons", headers=admin).json()
    client.post(f"{BASE}/reasons/{reasons[0]['id']}/deactivate", headers=admin)
    plans = client.get(f"{BASE}/plans", headers=admin).json()
    client.patch(f"{BASE}/plans/{plans[0]['id']}", headers=admin,
                 json={"monthly_price_rupees": 1111})

    with Session(engine) as db:
        again = seed_defaults(db)
        assert all(count == 0 for count in again.values()), again
        assert db.scalar(select(ChecklistItem).where(
            ChecklistItem.service == "Cleaning-External", ChecklistItem.key == "body")
        ).active is False
        assert lookup.setting(db, "schedule.unfreeze_code") == "sesame"
        assert db.scalar(select(CncReason).where(CncReason.key == "car_not_in_spot")
                         ).active is False
        assert len(list(db.scalars(select(WorkingSlot)))) == 3  # the demo society only
    assert client.get(f"{BASE}/plans", headers=admin).json()[0]["monthly_price_rupees"] == 1111


def test_seed_without_starter_data_adds_no_plan_addon_or_catalogue(engine, client, db):
    added = seed_defaults(db, starter_data=False)
    assert added["plans"] == added["addons"] == added["catalogue"] == 0
    assert not list(db.scalars(select(Plan)))
    assert not list(db.scalars(select(AddonCatalogueItem)))
    assert not list(db.scalars(select(VehicleCatalogueEntry)))
    # The rest the apps need is still there.
    assert added["services"] == 3 and added["reasons"] == len(defaults.REASONS)


def test_a_renamed_default_plan_is_not_added_again(client, admin, engine):
    with Session(engine) as db:
        seed_defaults(db)
    plans = client.get(f"{BASE}/plans", headers=admin).json()
    client.patch(f"{BASE}/plans/{plans[0]['id']}", headers=admin, json={"name": "Renamed"})
    with Session(engine) as db:
        # On a non-prod server the name check would add a second PLN-0001.
        seed_defaults(db, starter_data=False)
        assert [p.name for p in db.scalars(select(Plan))] == ["Renamed"]


def test_seed_leaves_a_table_alone_once_it_has_rows(engine, client, db):
    seed_defaults(db)
    db.delete(db.scalar(select(DirectoryService).where(DirectoryService.name == "Deep Spa")))
    db.delete(db.scalar(select(SystemSetting).where(SystemSetting.key == "support.hours")))
    db.delete(db.scalar(select(ChecklistItem).where(ChecklistItem.service == "Deep Spa")))
    db.commit()
    again = seed_defaults(db)
    assert again["services"] == again["settings"] == again["checklist_items"] == 0
    assert db.scalar(select(DirectoryService).where(DirectoryService.name == "Deep Spa")) is None
    assert db.get(SystemSetting, "support.hours") is None
    assert lookup.setting(db, "support.hours")  # A missing key still reads as its default.


def test_seed_adds_slots_only_while_no_slots_exist_at_all(client, admin, engine):
    made = society(client, admin)
    with Session(engine) as db:
        assert seed_defaults(db)["slots"] == 0  # The new society already has its slots.
    other = society(client, admin, name="Lake View")
    slots = client.get(f"{BASE}/societies/{other['id']}/slots", headers=admin).json()
    assert len(slots) == 3
    for s in client.get(f"{BASE}/societies/{made['id']}/slots", headers=admin).json():
        client.delete(f"{BASE}/slots/{s['id']}", headers=admin)
    with Session(engine) as db:
        # Removing one society's slots is the admin's change: other slots exist, so nothing is added.
        assert seed_defaults(db)["slots"] == 0
    for s in slots:
        client.delete(f"{BASE}/slots/{s['id']}", headers=admin)
    with Session(engine) as db:
        # With no slots anywhere the table counts as new.
        assert seed_defaults(db)["slots"] >= 6
