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
    # Dev only, until email is connected: no email is sent, and this fixed
    # 6-digit value is the code for every customer (AUTH-03). Never committed.
    mock_email_code: str = ""
    # Resend (email). With a key set, codes and the welcome email really go
    # out. Without one the logging fake is used. Never committed.
    resend_api_key: str = ""
    email_from: str = "Priveo <no-reply@priveo.in>"

    @property
    def fixed_email_code(self) -> str | None:
        code = self.mock_email_code.strip()
        if self.environment == "prod" or not (len(code) == 6 and code.isdigit()):
            return None
        return code


@lru_cache
def get_settings() -> Settings:
    return Settings()
