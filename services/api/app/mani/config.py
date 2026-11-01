"""Mani Bond settings. Read from the environment (and `.env`), never committed.

Local development uses the `local` backend (Ollama). `openrouter` is configuration
only until the owner says it is time to deploy to test."""
from functools import lru_cache

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# MANI_PROVIDER picks the model route. Each provider uses its own key and address.
#   localllm    Ollama on this machine; no key
#   openrouter  OpenRouter; PRIVEO_OPEN_ROUTER_TEST_KEY (or MANI_API_KEY)
#   google      Google's Gemini API directly; GEMINI_API_KEY (or MANI_API_KEY)
#   awsbedrock  not built yet (architecture D16, after the MVP)
PROVIDERS = {"localllm": "local", "openrouter": "openrouter", "google": "google", "awsbedrock": "awsbedrock"}
BACKENDS = ("local", "openrouter", "google")  # the routes with an adapter today
# Every index is vector(1024) on every backend (decision D15). Both backends are asked
# for this size, because their native size (4096) is more than pgvector can index.
EMBEDDING_DIMENSIONS = 1024
LOCAL_BASE_URL = "http://localhost:11434/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
GOOGLE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"  # Gemini's OpenAI-compatible API


class ManiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_prefix="MANI_")

    # The only login that may use Mani (D6). Anyone holding its password is the Founder.
    founder_login_id: str = "priveopapa"
    # Whether Mani Bond and the Agent report are on in the admin portal (MANI_PORTAL_ENABLED). Unset means
    # on in dev (local) and test, and off in prod. Set it to true or false to override either way.
    portal_enabled: bool | None = None
    # Which model route to use: localllm, openrouter, google or awsbedrock. Empty falls back to `backend`.
    provider: str = ""
    backend: str = "local"
    # Ollama's OpenAI-compatible endpoint, or OpenRouter's.
    base_url: str = LOCAL_BASE_URL
    # qwen3:14b with a 16,384-token window (scripts/setup_mani_models.sh). Ollama's own default of 4,096
    # tokens is smaller than the persona, the tool list and eight passages, so the prompt would be cut.
    chat_model: str = "qwen3-14b-16k"
    embedding_model: str = "qwen3-embedding:8b"
    # Where the embeddings come from. Empty means the same backend and URL as the chat. Set
    # MANI_EMBEDDING_BACKEND=local to keep embeddings on Ollama while the chat uses OpenRouter: the
    # stored vectors were made by the local model, so a question must be embedded by it too.
    embedding_backend: str = ""
    embedding_base_url: str = ""
    # Evaluation only (MANI_EVAL_ALLOW_DATA_RETENTION=true): lets OpenRouter use a provider that may keep
    # prompts, which the free models need. Off by default; never set it in test or prod (D8).
    eval_allow_data_retention: bool = False
    # Read for the hosted routes only (`openrouter`, `google`). Never committed.
    api_key: str = Field(default="", validation_alias=AliasChoices(
        "PRIVEO_OPEN_ROUTER_TEST_KEY", "MANI_API_KEY"))
    gemini_api_key: str = Field(default="", validation_alias=AliasChoices("GEMINI_API_KEY", "MANI_GEMINI_API_KEY"))
    # Total usage limit in US dollars for this environment, with no time period (D18).
    # When it is used up Mani stops calling the model. The owner raises it here.
    budget_usd: float = 1.0
    per_request_budget_usd: float = 0.0  # 0 means no per-request limit
    max_tool_rounds: int = 6
    request_timeout_seconds: float = 120.0
    conversation_retention_days: int = 90


    @model_validator(mode="after")
    def _apply_provider(self) -> "ManiSettings":
        """MANI_PROVIDER chooses the route, its address and which key is used."""
        if not self.provider:
            return self
        if self.provider not in PROVIDERS:
            raise ValueError(f"MANI_PROVIDER must be one of: {', '.join(PROVIDERS)}.")
        self.backend = PROVIDERS[self.provider]
        if "base_url" not in self.model_fields_set:
            urls = {"openrouter": OPENROUTER_BASE_URL, "google": GOOGLE_BASE_URL}
            self.base_url = urls.get(self.backend, LOCAL_BASE_URL)
        if self.backend == "google":
            self.api_key = self.gemini_api_key or self.api_key
        return self

    @property
    def embeddings_backend(self) -> str:
        # Google has no model matching the stored vectors, so its embeddings stay local unless told otherwise.
        return self.embedding_backend or ("local" if self.backend == "google" else self.backend)

    @property
    def embeddings_base_url(self) -> str:
        if self.embedding_base_url:
            return self.embedding_base_url
        if self.embeddings_backend != self.backend:
            return LOCAL_BASE_URL if self.embeddings_backend == "local" else OPENROUTER_BASE_URL
        return self.base_url

    def portal_on(self, environment: str) -> bool:
        """Whether the portal may show Mani and the Agent report in this environment."""
        return self.portal_enabled if self.portal_enabled is not None else environment != "prod"


@lru_cache
def get_mani_settings() -> ManiSettings:
    return ManiSettings()
