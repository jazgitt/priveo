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
    token_secret: str = "change-me"
    access_token_minutes: int = 15
    # The seeded admin's password (ADM-ACC-05). Never committed. The older
    # name MOCK_ADMIN_PASSWORD is still read.
    admin_password: str = Field(
        default="", validation_alias=AliasChoices("ADMIN_PASSWORD", "MOCK_ADMIN_PASSWORD"))
    # Dev only: seed a demo customer and a demo crew login with these passwords.
    seed_demo_logins: bool = False
    mock_customer_password: str = ""
    mock_crew_password: str = ""
    # "dev" or "prod". The dev-only switches below do nothing in "prod".
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
