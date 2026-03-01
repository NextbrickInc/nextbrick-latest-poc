# backend/app/config.py
# ─────────────────────────────────────────────────────────────────────────────
# Single source of truth for all runtime configuration.
# pydantic-settings reads values from environment variables (or .env file).
# Import the `settings` singleton anywhere in the app package.
# ─────────────────────────────────────────────────────────────────────────────
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── App meta ──────────────────────────────────────────────────────────────
    app_name: str = "Nextbrick Agentic AI"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # ── On-prem / local LLM (Ollama / vLLM) ──────────────────────────────────
    onprem_model_url: Optional[str] = None      # e.g. http://localhost:11434
    onprem_model_name: str = "qwen2.5-coder:latest"
    onprem_model_api_key: str = "EMPTY"

    # Legacy aliases (backwards compat with existing .env)
    model_url: Optional[str] = None
    model_name: Optional[str] = None
    model_api_key: Optional[str] = None

    # ── Cloud LLM (Anthropic / OpenAI) ───────────────────────────────────────
    cloud_model_url: Optional[str] = None
    cloud_model_name: Optional[str] = "claude-sonnet-4-5"
    cloud_model_api_key: Optional[str] = None

    # ── Elasticsearch ─────────────────────────────────────────────────────────
    es_host: str = "http://localhost:9200"
    es_index: str = "nextbrick-poc"
    es_username: Optional[str] = None
    es_password: Optional[str] = None
    es_cloud_id: Optional[str] = None
    es_cloud_api_key: Optional[str] = None

    # ── CORS ──────────────────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:8080"
    cors_origins: list[str] = ["*"]

    # ── LLM behaviour ─────────────────────────────────────────────────────────
    llm_temperature: float = 0.2
    llm_max_retries: int = 3
    llm_timeout_seconds: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Computed helpers ──────────────────────────────────────────────────────

    @property
    def effective_model_url(self) -> Optional[str]:
        return self.onprem_model_url or self.model_url

    @property
    def effective_model_name(self) -> str:
        return self.model_name or self.onprem_model_name

    @property
    def effective_api_key(self) -> str:
        return self.model_api_key or self.onprem_model_api_key or "EMPTY"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return cached Settings singleton.
    Call `get_settings.cache_clear()` in tests to reset.
    """
    return Settings()


# Convenience singleton for direct imports
settings: Settings = get_settings()
