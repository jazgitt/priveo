"""SCHS-18: the Scheduling rules panel's API (SCHR-CFG-02, SCHR-CFG-10, SCHR-CUT-06)."""
import pytest
from sqlalchemy import select

from app.directory import lookup, rule_seed, settings_registry
from app.directory.models import DirectoryAudit
from tests.test_api import auth, login

URL = "/v1/admin/scheduling/site-settings"


@pytest.fixture
def seeded(world):
    rule_seed.seed_rule_keys(world.db)
    world.db.commit()
    lookup.invalidate()


def _by_key(rows):
    return {r["key"]: r for r in rows}


def test_SCHR_CFG_10_every_site_key_is_listed_with_default_site_value_and_range(api, admin, world, seeded):
    r = api.get(URL, headers=admin, params={"society_id": str(world.society.id)})
    assert r.status_code == 200, r.text
    rows = _by_key(r.json())
    site_keys = {d.key for d in settings_registry.RULE_DEFINITIONS
                 if d.site and d.key.startswith("site.")}
    assert set(rows) == site_keys
    assert "scheduler.rules_version" not in rows  # the kill switch is not a panel value
    first = rows["site.first_job_minute"]
    assert first["default_value"] == "330" and first["site_value"] is None and first["value"] == "330"
    assert (first["minimum"], first["maximum"]) == (0, 1439)
    assert rows["site.break_enabled"]["kind"] == "bool" and rows["site.break_enabled"]["minimum"] is None


def test_SCHR_CFG_02_saving_a_value_changes_that_site_and_writes_an_audit_row(api, admin, world, seeded):
    sid = str(world.society.id)
    r = api.put(f"{URL}/site.first_job_minute", headers=admin, json={"society_id": sid, "value": "345"})
    assert r.status_code == 200, r.text
    assert r.json()["site_value"] == "345" and r.json()["value"] == "345"
    assert r.json()["default_value"] == "330"
    rows = _by_key(api.get(URL, headers=admin, params={"society_id": sid}).json())
    assert rows["site.first_job_minute"]["site_value"] == "345"
    audit = world.db.scalars(select(DirectoryAudit).where(
        DirectoryAudit.entity == "society_setting", DirectoryAudit.entity_id == "site.first_job_minute")).all()
    assert [a.detail for a in audit] == [{"value": ["330", "345"]}]


def test_SCHR_CFG_02_a_bool_and_weekdays_value_are_saved_as_text(api, admin, world, seeded):
    sid = str(world.society.id)
    r = api.put(f"{URL}/site.break_enabled", headers=admin, json={"society_id": sid, "value": "false"})
    assert r.status_code == 200 and r.json()["value"] == "false"
    r = api.put(f"{URL}/site.weekend_weekdays", headers=admin, json={"society_id": sid, "value": "6,5"})
    assert r.status_code == 200 and r.json()["value"] == "5,6"


def test_SCHR_CFG_02_an_invalid_value_shows_the_message_and_saves_nothing(api, admin, world, seeded):
    sid = str(world.society.id)
    r = api.put(f"{URL}/site.first_job_minute", headers=admin, json={"society_id": sid, "value": "2000"})
    assert r.status_code == 422
    assert r.json()["fields"]["value"] == "Enter a number from 0 to 1439."
    r = api.put(f"{URL}/site.first_job_minute", headers=admin, json={"society_id": sid, "value": "280"})
    assert r.status_code == 422  # before the reporting time (site rule)
    assert "reporting time" in r.json()["message"]
    rows = _by_key(api.get(URL, headers=admin, params={"society_id": sid}).json())
    assert rows["site.first_job_minute"]["site_value"] is None


def test_SCHR_CUT_06_unknown_keys_global_keys_and_non_admins_are_refused(api, admin, world, seeded):
    sid = str(world.society.id)
    assert api.put(f"{URL}/site.nope", headers=admin, json={"society_id": sid, "value": "1"}).status_code == 404
    assert api.put(f"{URL}/scheduler.rules_version", headers=admin,
                   json={"society_id": sid, "value": "2"}).status_code == 404
    cust = auth(login(api, "customer")["access_token"])
    assert api.get(URL, headers=cust, params={"society_id": sid}).status_code == 403
