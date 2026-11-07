"""SCHS-02: per-site scheduler settings, key registry, lookup and seeding."""
import pytest
from sqlalchemy import select

from app.directory import lookup, rule_seed, settings_registry, site_settings
from app.directory.models import DirectoryAudit, Society, SystemSetting
from app.directory.seed import seed_defaults
from app.identity.models import Login
from app.identity.seed import seed_logins

NEW_KEYS = {d.key for d in settings_registry.RULE_DEFINITIONS}


@pytest.fixture
def two_sites(db):
    a, b = Society(name="Site A"), Society(name="Site B")
    db.add_all([a, b])
    db.commit()
    return a, b


@pytest.fixture
def admin_id(db, settings):
    seed_logins(db, settings)
    return db.scalar(select(Login.id).where(Login.role == "admin"))


@pytest.fixture
def seeded(db):
    rule_seed.seed_rule_keys(db)
    db.commit()
    lookup.invalidate()


def test_schr_cfg_03_registry_defines_every_new_key_once_with_requirements_defaults():
    keys = [d.key for d in settings_registry.DEFINITIONS]
    assert len(keys) == len(set(keys))
    expected = {
        "scheduler.grid_minutes": 5,
        "scheduler.solve_seconds": 10, "scheduler.seed": 7, "scheduler.workers": 1,
        "scheduler.retry_minutes_running": 30, "scheduler.retry_minutes_error": 5,
        "site.reporting_minute": 300, "site.first_job_minute": 330,
        "site.interior_earliest_minute": 420, "site.break_start_minute": 570,
        "site.break_end_minute": 600, "schedule.interior_entitlement_per_week": 1,
        "schedule.service_week_start": 0,
    }
    for key, value in expected.items():
        assert settings_registry.BY_KEY[key].default == value, key
    for key in ("site.break_enabled", "site.weekday_cutoff_hard",
                "site.weekend_cutoff_flexible", "site.cross_zone_help_allowed"):
        assert settings_registry.BY_KEY[key].default is True
    assert settings_registry.BY_KEY["site.weekend_weekdays"].default == "5,6"


def test_schr_cfg_03_seed_adds_missing_keys_then_nothing(db):
    assert rule_seed.seed_rule_keys(db) == len(NEW_KEYS)
    db.commit()
    assert rule_seed.seed_rule_keys(db) == 0
    assert db.get(SystemSetting, "site.break_enabled").value == "true"
    assert db.get(SystemSetting, "site.weekend_weekdays").value == "5,6"


def test_schr_cfg_03_seed_never_changes_an_edited_value(db):
    db.add(SystemSetting(key="scheduler.grid_minutes", value="10"))
    db.commit()
    rule_seed.seed_rule_keys(db)
    db.commit()
    assert db.get(SystemSetting, "scheduler.grid_minutes").value == "10"
    seed_defaults(db)
    seed_defaults(db)
    assert db.get(SystemSetting, "scheduler.grid_minutes").value == "10"


def test_schr_cfg_03_seed_defaults_adds_new_keys_to_an_existing_settings_table(db):
    db.add(SystemSetting(key="billing.cycle_days", value="30"))  # an older release's table
    db.commit()
    seed_defaults(db)
    assert NEW_KEYS <= {r.key for r in db.scalars(select(SystemSetting))}


def test_schr_par_01_site_value_overrides_global(db, two_sites, seeded, admin_id):
    a, b = two_sites
    assert lookup.site_setting(db, a.id, "site.first_job_minute") == 330
    site_settings.write(db, a.id, "site.first_job_minute", 360, admin_id)
    assert lookup.site_setting(db, a.id, "site.first_job_minute") == 360
    assert lookup.site_setting(db, b.id, "site.first_job_minute") == 330  # other site unchanged
    row = db.get(SystemSetting, "site.first_job_minute")
    assert row.value == "330"  # the global default is untouched


def test_schr_par_01_typed_values(db, two_sites, seeded):
    a, _ = two_sites
    assert lookup.site_setting(db, a.id, "site.break_enabled") is True
    assert lookup.site_setting(db, a.id, "site.weekend_weekdays") == [5, 6]
    assert len(lookup.site_settings_all(db, a.id)) == len(NEW_KEYS)


def test_schr_cfg_04_missing_key_raises_and_no_hidden_default(db, two_sites):
    a, _ = two_sites  # nothing seeded
    with pytest.raises(site_settings.SettingMissing, match="site.reporting_minute"):
        lookup.site_setting(db, a.id, "site.reporting_minute")
    with pytest.raises(site_settings.SettingError, match="does not exist"):
        lookup.site_setting(db, a.id, "site.nope")


def test_schr_par_14_global_only_key_cannot_be_set_for_a_site(db, two_sites, seeded, admin_id):
    with pytest.raises(site_settings.SettingError, match="all sites"):
        site_settings.write(db, two_sites[0].id, "scheduler.grid_minutes", 10, admin_id)


@pytest.mark.parametrize("key,value", [
    ("site.first_job_minute", 1440), ("site.first_job_minute", -1),
    ("site.first_job_minute", "soon"), ("site.break_enabled", "maybe"),
    ("site.weekend_weekdays", "5,9"), ("site.weekend_weekdays", "5,5"),
])
def test_schr_cfg_05_out_of_range_or_malformed_is_refused(db, two_sites, seeded, admin_id,
                                                          key, value):
    with pytest.raises(ValueError) as exc:
        site_settings.write(db, two_sites[0].id, key, value, admin_id)
    assert str(exc.value)
    assert db.scalar(select(DirectoryAudit.id)) is None


def test_schr_cfg_05_consistency_of_times(db, two_sites, seeded, admin_id):
    sid = two_sites[0].id
    with pytest.raises(site_settings.SettingError, match="break must start before"):
        site_settings.write(db, sid, "site.break_start_minute", 600, admin_id)
    with pytest.raises(site_settings.SettingError, match="first job cannot be before"):
        site_settings.write(db, sid, "site.first_job_minute", 290, admin_id)
    with pytest.raises(site_settings.SettingError, match="Interior cannot start before"):
        site_settings.write(db, sid, "site.interior_earliest_minute", 300, admin_id)
    site_settings.write(db, sid, "site.interior_earliest_minute", 330, admin_id)  # equal is fine


def test_schr_cfg_06_each_save_writes_an_audit_row(db, two_sites, seeded, admin_id):
    a, _ = two_sites
    site_settings.write(db, a.id, "site.reporting_minute", 290, admin_id)
    site_settings.write(db, a.id, "site.reporting_minute", "295", admin_id)
    rows = list(db.scalars(select(DirectoryAudit).order_by(DirectoryAudit.at)))
    assert len(rows) == 2
    first, second = rows
    assert first.society_id == a.id and first.admin_login_id == admin_id
    assert first.at is not None and first.entity == "society_setting"
    assert first.entity_id == "site.reporting_minute"
    assert first.detail == {"value": ["300", "290"]}
    assert second.detail == {"value": ["290", "295"]}
