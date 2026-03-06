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
    app_name: str = "Keysight Agentic AI"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # ── On-prem / local LLM (Ollama / vLLM) ──────────────────────────────────
    onprem_model_url: Optional[str] = None      # e.g. http://localhost:11434
    onprem_model_name: str = "gpt-oss:120b-cloud"
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
    es_index: str = "keysight-poc"
    es_username: Optional[str] = None
    es_password: Optional[str] = None
    es_cloud_id: Optional[str] = None
    es_cloud_api_key: Optional[str] = None

    # ── Salesforce (OAuth2 client_credentials + Data API) ─────────────────────
    sf_token_url: Optional[str] = None   # e.g. https://yourorg.my.salesforce.com/services/oauth2/token
    sf_client_id: Optional[str] = None
    sf_client_secret: Optional[str] = None
    sf_api_base_url: Optional[str] = None  # e.g. https://yourorg.my.salesforce.com/services/data/v60.0
    sf_default_case_account_id: Optional[str] = None  # optional; used when creating cases (default in tool)
    # Legacy (optional)
    sf_username: Optional[str] = None
    sf_password: Optional[str] = None
    sf_security_token: Optional[str] = None
    sf_domain: str = "login"

    # ── Confluence ────────────────────────────────────────────────────────────
    confluence_url: Optional[str] = None  # e.g. https://yourorg.atlassian.net
    confluence_username: Optional[str] = None
    confluence_api_token: Optional[str] = None
    confluence_space_key: str = "~"

    # ── Embeddings ────────────────────────────────────────────────────────────
    embedding_model: str = "text-embedding-3-small"
    es_vector_index: str = "keysight-vectors"
    # Main Elasticsearch data index (orders/cases/assets) — authoritative CSV/JSON snapshot
    es_data_index: str = "next_elastic_test1"

    # ── Ollama embeddings + test index (for elasticsearch_ollama_tool) ─────
    ollama_embedding_model: str = "bge-m3:latest"
    # Vector index that holds embedded docs from backend/docs
    es_ollama_index: str = "next_elastic_test3"

    # ── CORS ──────────────────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:8080"
    cors_origins: list[str] = ["*"]

    # ── Kafka ─────────────────────────────────────────────────────────────────
    kafka_enabled: bool = True
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_chat_events: str = "chat.events"
    kafka_topic_agent_events: str = "agent.events"


    # ── Caching ──────────────────────────────────────────────────────────────
    cache_ttl_search_seconds: int = 300  # 5 minutes for search/chat cache
    cache_ttl_faq_seconds: int = 3600    # 1 hour for FAQ cache
    cache_max_size: int = 1000

    # ── LLM behaviour ─────────────────────────────────────────────────────────
    llm_temperature: float = 0.2
    llm_max_retries: int = 2
    llm_timeout_seconds: int = 120  # allow slow/large models (e.g. 120B) to complete

    # ── Agent dynamic model selection ────────────────────────────────────────
    agent_advanced_message_threshold: int = 10  # use advanced model when messages > this
    chat_memory_max_messages: int = 5  # fewer messages = smaller prompt, faster response

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
