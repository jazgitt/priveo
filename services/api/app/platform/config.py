import logging
import os
from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_version: str = "0.1.0"
    build_number: str = "0"
    min_app_version: str = "0.1.0"
    # PostgreSQL address. The host may give it as postgres:// or postgresql://.
    database_url: str = ""
    # Signs every sign-in token. No fallback: the server refuses to start without
    # a real one (check_startup).
    token_secret: str = ""
    access_token_minutes: int = 15
    # The seeded admin's password (ADM-ACC-05). Never committed. The older
    # name MOCK_ADMIN_PASSWORD is still read.
    admin_password: str = Field(
        default="", validation_alias=AliasChoices("ADMIN_PASSWORD", "MOCK_ADMIN_PASSWORD"))
    # Dev only: seed a demo customer and a demo crew login with these passwords.
    seed_demo_logins: bool = False
    mock_customer_password: str = ""
    mock_crew_password: str = ""
    # "dev" or "prod". The dev-only switches below do nothing in "prod". On a
    # hosted server it must be set on purpose (check_startup); on a developer's
    # machine it defaults to "dev".
    environment: str = "dev"
    # Dev only: optional fixed 6-digit code for customer verification.
    # Delivery uses Resend when configured, otherwise the logging sender.
    mock_email_code: str = ""
    # Resend (email). With a key set, codes and the welcome email really go
    # out. Without one the logging fake is used. Never committed.
    resend_api_key: str = ""
    email_from: str = "Priveo <no-reply@priveo.in>"
    # Dev/testing: when set, every email goes to this address instead.
    email_redirect_to: str = ""
    # The public address of this deployment, for links in emails to admins
    # (for example https://priveo-api.vercel.app). Empty: emails carry no link.
    public_base_url: str = ""
    terms_url: str = "https://example.com/priveo/terms"
    privacy_url: str = "https://example.com/priveo/privacy"

    @property
    def fixed_email_code(self) -> str | None:
        code = self.mock_email_code.strip()
        if self.environment == "prod" or not (len(code) == 6 and code.isdigit()):
            return None
        return code


@lru_cache
def get_settings() -> Settings:
    return Settings()


log = logging.getLogger("priveo.api")

# Set by the hosts the API runs on: Vercel, and AWS (ECS Fargate).
_HOSTED_MARKERS = ("VERCEL", "AWS_EXECUTION_ENV", "ECS_CONTAINER_METADATA_URI_V4")
_ENVIRONMENTS = ("dev", "prod")
_MIN_PROD_SECRET = 32
_PLACEHOLDER_SECRETS = ("", "change-me")


class StartupError(RuntimeError):
    """The server was configured in a way that is not safe to run."""


def is_hosted() -> bool:
    return any(os.environ.get(name) for name in _HOSTED_MARKERS)


def startup_problems(settings: Settings, *, hosted: bool,
                     cron_secret: str = "") -> tuple[list[str], list[str]]:
    """What is wrong with the configuration: (problems that stop the server,
    warnings). Dev and prod are separate deployments. Only dev may have demo
    logins and the fixed sign-in code."""
    problems: list[str] = []
    warnings: list[str] = []
    secret = settings.token_secret.strip()
    if secret in _PLACEHOLDER_SECRETS:
        problems.append("TOKEN_SECRET is not set. Set it to a long random value.")
    if settings.environment not in _ENVIRONMENTS:
        problems.append('ENVIRONMENT must be exactly "dev" or "prod".')
    if hosted and "environment" not in settings.model_fields_set:
        problems.append('ENVIRONMENT is not set. A hosted server must say "dev" or "prod".')

    if settings.environment == "prod":
        if secret not in _PLACEHOLDER_SECRETS and len(secret) < _MIN_PROD_SECRET:
            problems.append(f"TOKEN_SECRET must be at least {_MIN_PROD_SECRET} characters in prod.")
        for name, value in (("SEED_DEMO_LOGINS", settings.seed_demo_logins),
                            ("MOCK_EMAIL_CODE", settings.mock_email_code.strip()),
                            ("MOCK_CUSTOMER_PASSWORD", settings.mock_customer_password),
                            ("MOCK_CREW_PASSWORD", settings.mock_crew_password),
                            ("EMAIL_REDIRECT_TO", settings.email_redirect_to.strip())):
            if value:
                problems.append(f"{name} is for dev only and must not be set in prod.")
        if not settings.resend_api_key.strip():
            problems.append("RESEND_API_KEY is not set. Customers could not sign in.")
        if not cron_secret.strip():
            problems.append("CRON_SECRET is not set. The scheduled jobs would not run.")
    else:
        if secret not in _PLACEHOLDER_SECRETS and len(secret) < _MIN_PROD_SECRET:
            warnings.append(f"TOKEN_SECRET is shorter than {_MIN_PROD_SECRET} characters.")
        if hosted and settings.mock_email_code.strip():
            warnings.append("MOCK_EMAIL_CODE is set on a hosted server: anyone who learns "
                            "it can reset a customer's password.")
    return problems, warnings


def check_startup(settings: Settings, *, cron_secret: str = "", hosted: bool | None = None) -> None:
    """Run when the server starts. Raises StartupError when the configuration
    is not safe, so a mistake stops the deploy instead of running quietly."""
    hosted = is_hosted() if hosted is None else hosted
    problems, warnings = startup_problems(settings, hosted=hosted, cron_secret=cron_secret)
    for warning in warnings:
        log.warning("startup: %s", warning)
    if problems:
        raise StartupError("Unsafe configuration: " + " ".join(problems))
    log.info("startup: environment=%s hosted=%s", settings.environment, hosted)
