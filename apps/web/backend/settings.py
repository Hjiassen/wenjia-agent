"""Web-transport settings for the backend (kept separate from agent-core config).

CORS is a web concern, so it lives here rather than in ``app.runtime.config``
which owns model/DB/harness settings for the agent core.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    """Runtime settings for the web backend."""

    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        alias="WENJIA_CORS_ORIGINS",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_comma_separated(cls, value: object) -> object:
        """Accept a comma-separated string so ``WENJIA_CORS_ORIGINS=a,b`` works."""

        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = BackendSettings()
