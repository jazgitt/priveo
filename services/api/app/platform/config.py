from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_version: str = "0.1.0"
    build_number: str = "0"
    min_app_version: str = "0.1.0"
    token_secret: str = "change-me"
    access_token_minutes: int = 30
    refresh_token_days: int = 30
    # Phase 0 mock passwords, set as configuration on the dev API, never committed.
    # An empty value switches that mock login off.
    mock_customer_password: str = ""
    mock_crew_password: str = ""
    mock_admin_password: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
