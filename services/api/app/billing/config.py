from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class MoneySettings(BaseSettings):
    """Where customers pay, and what is shown on an invoice. The values below
    are PLACEHOLDERS: the real UPI ID, QR image, seller details and GSTIN are
    environment configuration (MONEY_*), never committed."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="MONEY_", extra="ignore")

    upi_id: str = "priveo-placeholder@upi"
    upi_payee_name: str = "Priveo (placeholder)"
    # An image address for the QR code. Empty until the owner provides it.
    upi_qr_url: str = ""
    seller_name: str = "Priveo (placeholder seller)"
    seller_address: str = "Placeholder address"
    seller_gstin: str = "00PLACEHOLDER0Z0"
    # Placeholder price of the Deep Spa add-on, GST included (ADM-ADD-01).
    deep_spa_price_rupees: int = 1500
    deep_spa_list_price_rupees: int = 2000


@lru_cache
def get_money_settings() -> MoneySettings:
    return MoneySettings()
