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
    session_db_url: str = Field(
        default="sqlite+aiosqlite:///./wenjia_agent_sessions.db",
        alias="WENJIA_SESSION_DB_URL",
    )

    # Harness loop controls.
    harness_max_turns: int = Field(default=16, alias="WENJIA_HARNESS_MAX_TURNS")
    harness_max_revisions: int = Field(default=1, alias="WENJIA_HARNESS_MAX_REVISIONS")
    harness_revise_enabled: bool = Field(default=True, alias="WENJIA_HARNESS_REVISE")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
