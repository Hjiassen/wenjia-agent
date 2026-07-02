"""Runtime configuration."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_agent_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_AGENT_MODEL")
    openai_analysis_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_ANALYSIS_MODEL")
    openai_fallback_model: str = Field(default="", alias="OPENAI_FALLBACK_MODEL")
    session_db_url: str = Field(
        default="sqlite+aiosqlite:///./wenjia_agent_sessions.db",
        alias="WENJIA_SESSION_DB_URL",
    )

    # Harness loop controls.
    harness_max_turns: int = Field(default=16, alias="WENJIA_HARNESS_MAX_TURNS")
    harness_max_revisions: int = Field(default=1, alias="WENJIA_HARNESS_MAX_REVISIONS")
    harness_revise_enabled: bool = Field(default=True, alias="WENJIA_HARNESS_REVISE")
    harness_model_timeout_seconds: float = Field(
        default=90.0,
        alias="WENJIA_MODEL_TIMEOUT_SECONDS",
    )

    # Input safety.
    input_guardrails_enabled: bool = Field(
        default=True,
        alias="WENJIA_INPUT_GUARDRAILS_ENABLED",
    )
    input_max_chars: int = Field(default=8000, alias="WENJIA_INPUT_MAX_CHARS")

    # Long-term memory. ``client_id``/``user_id`` comes from the embedding app;
    # this project still does not implement accounts.
    long_term_memory_enabled: bool = Field(
        default=True,
        alias="WENJIA_LONG_TERM_MEMORY_ENABLED",
    )
    long_term_memory_max_items: int = Field(default=8, alias="WENJIA_LONG_TERM_MEMORY_MAX_ITEMS")

    # Local observability. The SDK trace API remains opt-in; local JSONL traces
    # are cheap and do not require external services.
    trace_enabled: bool = Field(default=True, alias="WENJIA_TRACE_ENABLED")
    trace_dir: str = Field(default="logs/traces", alias="WENJIA_TRACE_DIR")
    openai_sdk_tracing_enabled: bool = Field(
        default=False,
        alias="WENJIA_OPENAI_SDK_TRACING",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
