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


@lru_cache
def get_settings() -> Settings:
    return Settings()
