"""Small, idempotent schema initialization for the authenticated web app."""

from __future__ import annotations

from apps.web.backend.modules import auth_store, profile_store
from wenjia_agent.runtime import memory_store


def run_migrations() -> dict[str, int | bool]:
    """Create only the current account, profile, and memory tables.

    ``create_all`` is intentionally used here because the project supports
    SQLite deployments without an external migration runner. Only current
    authenticated tables are initialized.
    """

    auth_store.init_db()
    profile_store.init_db()
    memory_store.init_db()
    return {
        "schema_ready": True,
    }
