from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.web.backend.modules import auth_store, conversation_store, migrations
from apps.web.backend.modules import profile_store as account_profile_store
from wenjia_agent.runtime import memory_store


def test_migrations_are_idempotent_without_legacy_guest_tables(monkeypatch, tmp_path):
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    engine = create_engine(url, future=True)
    factory = sessionmaker(bind=engine, future=True)
    for store in (auth_store, conversation_store, account_profile_store, memory_store):
        monkeypatch.setattr(store, "_engine", engine)
        monkeypatch.setattr(store, "_Session", factory)
        monkeypatch.setattr(store, "_initialized", False)
    first = migrations.run_migrations()
    second = migrations.run_migrations()

    assert first["schema_ready"] is True
    assert second["schema_ready"] is True
