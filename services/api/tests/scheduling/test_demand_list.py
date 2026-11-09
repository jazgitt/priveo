"""P3-2.2: the Demand tab's list. Exteriors by cutoff, then Interiors by cutoff,
then the other services by cutoff; skipped demand is left out; the endpoint
filters by service and date."""
from datetime import time, timedelta

from app.scheduling import demand_list
from app.scheduling.service import Demand
from tests.scheduling.conftest import SUNDAY

BASE = "/v1/admin/scheduling"
EXT, INT, SPA = "Cleaning-External", "Cleaning-Internal", "Deep Spa"


def _order(rows):
    return [(r.service, r.cutoff) for r in rows]


def test_exteriors_then_interiors_then_others_each_by_cutoff(world, monkeypatch):
    v1, v2, v3 = (world.add_vehicle(cutoff=time(10, 0)), world.add_vehicle(cutoff=time(8, 0)),
                  world.add_vehicle(cutoff=time(9, 0)))
    world.db.commit()
    due = [
        Demand(SUNDAY, v1.id, SPA, 7 * 60),
        Demand(SUNDAY, v1.id, INT, 9 * 60),
        Demand(SUNDAY, v1.id, EXT, 10 * 60),
        Demand(SUNDAY, v2.id, EXT, 8 * 60),
        Demand(SUNDAY, v3.id, INT, 6 * 60),
        Demand(SUNDAY, v3.id, SPA, None, addon_request_id=None),
        Demand(SUNDAY, v3.id, EXT, 9 * 60),
    ]
    monkeypatch.setattr(demand_list.service, "build_demand", lambda db, soc, days: due)
    rows = demand_list.due_on(world.db, world.society.id, SUNDAY)
    assert _order(rows) == [
        (EXT, "08:00"), (EXT, "09:00"), (EXT, "10:00"),
        (INT, "06:00"), (INT, "09:00"),
        (SPA, "07:00"), (SPA, None),
    ]


def test_skipped_demand_is_left_out(world, monkeypatch):
    v1 = world.add_vehicle(cutoff=time(10, 0))
    world.db.commit()
    due = [Demand(SUNDAY, v1.id, EXT, 600, skipped=True), Demand(SUNDAY, v1.id, INT, 660)]
    monkeypatch.setattr(demand_list.service, "build_demand", lambda db, soc, days: due)
    assert _order(demand_list.due_on(world.db, world.society.id, SUNDAY)) == [(INT, "11:00")]


def test_endpoint_lists_real_demand_in_order(api, admin, world):
    early = world.add_vehicle(cutoff=time(8, 0))
    late = world.add_vehicle(cutoff=time(10, 0), interior_day="Sunday")
    world.db.commit()
    r = api.get(f"{BASE}/demand", headers=admin,
                params={"society_id": str(world.society.id), "date": SUNDAY.isoformat()})
    assert r.status_code == 200, r.text
    items = r.json()
    assert [(i["service"], i["cutoff"]) for i in items] == [
        (EXT, "08:00"), (EXT, "10:00"), (INT, "10:00")]
    assert items[0]["vehicle_id"] == str(early.id)
    assert items[1]["vehicle_id"] == str(late.id)
    assert items[0]["group"] == "EXT" and items[2]["group"] == "INT"
    assert items[0]["service_label"] == "Exterior" and items[2]["service_label"] == "Interior"
    assert items[0]["source"] == "Subscription"


def test_endpoint_filters_by_service_and_date(api, admin, world):
    world.add_vehicle(cutoff=time(8, 0), interior_day="Sunday")
    world.db.commit()
    params = {"society_id": str(world.society.id), "date": SUNDAY.isoformat(), "service": INT}
    only_int = api.get(f"{BASE}/demand", headers=admin, params=params).json()
    assert [i["service"] for i in only_int] == [INT]
    next_day = (SUNDAY + timedelta(days=1)).isoformat()
    other = api.get(f"{BASE}/demand", headers=admin,
                    params={"society_id": str(world.society.id), "date": next_day}).json()
    assert all(i["cutoff"] == "08:00" for i in other) and {i["service"] for i in other} == {EXT}
