"""Helpers for SDK-backed short-term conversation memory."""

from __future__ import annotations

from agents.memory.session_settings import SessionSettings

from wenjia_agent.runtime.config import settings


def build_session_settings() -> SessionSettings | None:
    """Return SDK session settings for bounded short-term memory retrieval."""

    limit = settings.session_history_limit
    if limit is None or limit <= 0:
        return None
    return SessionSettings(limit=limit)
