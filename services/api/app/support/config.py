from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class SupportSettings(BaseSettings):
    """Support contact details. Placeholders until Priveo supplies the real
    numbers (SUP-02, SUP-03): set SUPPORT_HELPLINE and SUPPORT_WHATSAPP."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    support_helpline: str = "+910000000000"
    support_whatsapp: str = "+910000000000"
    support_hours: str = "6 AM to 10 PM"  # SUP-04


@lru_cache
def get_support_settings() -> SupportSettings:
    return SupportSettings()
