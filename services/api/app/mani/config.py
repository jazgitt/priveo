"""Mani Bond settings. Read from the environment (and `.env`), never committed.

Local development uses the `local` backend (Ollama). `openrouter` is configuration
only until the owner says it is time to deploy to test."""
from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKENDS = ("local", "openrouter")
# Every index is vector(1024) on every backend (decision D15). Both backends are asked
# for this size, because their native size (4096) is more than pgvector can index.
EMBEDDING_DIMENSIONS = 1024


class ManiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_prefix="MANI_")

    # The only login that may use Mani (D6). Anyone holding its password is the Founder.
    founder_login_id: str = "priveopapa"
    backend: str = "local"
    # Ollama's OpenAI-compatible endpoint, or OpenRouter's.
    base_url: str = "http://localhost:11434/v1"
    # qwen3:14b with a 16,384-token window (scripts/setup_mani_models.sh). Ollama's own default of 4,096
    # tokens is smaller than the persona, the tool list and eight passages, so the prompt would be cut.
    chat_model: str = "qwen3-14b-16k"
    embedding_model: str = "qwen3-embedding:8b"
    # Only read for the `openrouter` backend. Never committed.
    api_key: str = Field(default="", validation_alias=AliasChoices(
        "PRIVEO_OPEN_ROUTER_TEST_KEY", "MANI_API_KEY"))
    # Total usage limit in US dollars for this environment, with no time period (D18).
    # When it is used up Mani stops calling the model. The owner raises it here.
    budget_usd: float = 1.0
    per_request_budget_usd: float = 0.0  # 0 means no per-request limit
    max_tool_rounds: int = 6
    request_timeout_seconds: float = 120.0
    conversation_retention_days: int = 90


@lru_cache
def get_mani_settings() -> ManiSettings:
    return ManiSettings()
