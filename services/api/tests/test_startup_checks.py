"""The server refuses to start with an unsafe configuration. Dev and prod are
separate deployments: only dev may hold demo logins and the fixed sign-in code."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.identity.models import Login
from app.identity.seed import seed_logins
from app.main import create_app
from app.platform.config import Settings, StartupError, check_startup, startup_problems

STRONG = "a-long-random-secret-of-more-than-32-characters"


def make(**values) -> Settings:
    base = {"token_secret": STRONG, "environment": "dev"}
    return Settings(_env_file=None, **{**base, **values})


def prod(**values) -> Settings:
    base = {"environment": "prod", "resend_api_key": "re_test"}
    return make(**{**base, **values})


def problems(settings, hosted=False, cron="cron-secret"):
    return startup_problems(settings, hosted=hosted, cron_secret=cron)[0]


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in ("ENVIRONMENT", "SEED_DEMO_LOGINS", "MOCK_EMAIL_CODE", "EMAIL_REDIRECT_TO",
                 "MOCK_CUSTOMER_PASSWORD", "MOCK_CREW_PASSWORD", "RESEND_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def test_a_good_dev_setup_has_no_problems():
    assert problems(make()) == []


def test_there_is_no_fallback_secret():
    assert Settings(_env_file=None).token_secret == ""


@pytest.mark.parametrize("secret", ["", "   ", "change-me"])
def test_a_missing_or_placeholder_secret_stops_the_server(secret):
    assert any("TOKEN_SECRET" in p for p in problems(make(token_secret=secret)))
    assert any("TOKEN_SECRET" in p for p in problems(prod(token_secret=secret)))


def test_a_short_secret_stops_prod_but_only_warns_on_dev():
    assert any("32 characters" in p for p in problems(prod(token_secret="short-secret")))
    found, warnings = startup_problems(make(token_secret="short-secret"), hosted=False)
    assert found == [] and any("shorter than 32" in w for w in warnings)


@pytest.mark.parametrize("value", ["", "Prod", "production", "staging"])
def test_the_environment_must_be_exactly_dev_or_prod(value):
    assert any("ENVIRONMENT must be exactly" in p for p in problems(make(environment=value)))


def test_a_hosted_server_must_set_the_environment_on_purpose(monkeypatch):
    # Not set: the default "dev" must not be used silently on a hosted server.
    settings = Settings(_env_file=None, token_secret=STRONG)
    assert any("ENVIRONMENT is not set" in p for p in problems(settings, hosted=True))
    assert problems(settings, hosted=False) == []
    # Set on purpose, even to dev.
    assert problems(make(), hosted=True) == []


def test_a_good_prod_setup_has_no_problems():
    assert problems(prod(), hosted=True) == []


@pytest.mark.parametrize("name,value", [
    ("seed_demo_logins", True),
    ("mock_email_code", "123456"),
    ("mock_customer_password", "pw"),
    ("mock_crew_password", "pw"),
    ("email_redirect_to", "me@example.com"),
])
def test_dev_only_settings_stop_a_prod_server(name, value):
    found = problems(prod(**{name: value}), hosted=True)
    assert any(name.upper() in p and "dev only" in p for p in found)


def test_prod_needs_email_and_the_cron_secret():
    found = problems(prod(resend_api_key=""), hosted=True, cron="")
    assert any("RESEND_API_KEY" in p for p in found)
    assert any("CRON_SECRET" in p for p in found)


def test_dev_may_keep_demo_logins_and_the_fixed_code():
    settings = make(seed_demo_logins=True, mock_email_code="123456")
    assert problems(settings, hosted=True) == []


def test_a_fixed_code_on_a_hosted_dev_server_is_warned_about():
    _, warnings = startup_problems(make(mock_email_code="123456"), hosted=True)
    assert any("MOCK_EMAIL_CODE" in w for w in warnings)
    _, warnings = startup_problems(make(mock_email_code="123456"), hosted=False)
    assert warnings == []


def test_check_startup_raises_with_every_problem_named():
    with pytest.raises(StartupError) as raised:
        check_startup(prod(token_secret="", seed_demo_logins=True), hosted=True)
    message = str(raised.value)
    assert "TOKEN_SECRET" in message and "SEED_DEMO_LOGINS" in message


def test_the_app_will_not_start_with_an_unsafe_setup(monkeypatch):
    from app.platform.config import get_settings
    monkeypatch.setenv("TOKEN_SECRET", "change-me")
    get_settings.cache_clear()
    try:
        with pytest.raises(StartupError):
            with TestClient(create_app()):
                pass
    finally:
        get_settings.cache_clear()


def test_the_app_starts_with_a_safe_setup(settings):
    with TestClient(create_app()) as client:
        assert client.get("/v1/public/health").status_code == 200


def test_demo_logins_are_never_seeded_in_prod(db, settings, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "prod")
    from app.platform.config import get_settings
    get_settings.cache_clear()
    done = seed_logins(db, get_settings())
    assert done["demo logins"].startswith("skipped")
    assert db.scalar(select(Login).where(Login.role == "crew")) is None
    assert db.scalar(select(Login).where(Login.role == "customer")) is None
    # The admin is still made.
    assert db.scalar(select(Login).where(Login.role == "admin")) is not None
