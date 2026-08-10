from __future__ import annotations

import asyncio

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.web.backend.main import app
from apps.web.backend.modules import auth_store
from wenjia_agent.runtime import memory_store


@pytest.fixture()
def memory_api_db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'memory-api.db'}", future=True)
    factory = sessionmaker(bind=engine, future=True)
    monkeypatch.setattr(auth_store, "_engine", engine)
    monkeypatch.setattr(auth_store, "_Session", factory)
    monkeypatch.setattr(auth_store, "_initialized", False)
    monkeypatch.setattr(memory_store, "_engine", engine)
    monkeypatch.setattr(memory_store, "_Session", factory)
    monkeypatch.setattr(memory_store, "_initialized", False)
    auth_store.init_db()
    memory_store.init_db()
    return engine


async def _register(client: httpx.AsyncClient, username: str) -> None:
    response = await client.post(
        "/api/auth/register",
        json={"username": username, "password": "secure-pass-123", "confirm_password": "secure-pass-123"},
    )
    assert response.status_code == 201


def test_authenticated_memory_crud_and_profile_kind_rejection(memory_api_db):
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await _register(client, "Alice")
            created = await client.post(
                "/api/memories",
                json={
                    "kind": "preference",
                    "key": "preference:style",
                    "title": "回答偏好",
                    "content": "以后先给结论。",
                },
            )
            memory_id = created.json()["memory"]["id"]
            listed = await client.get("/api/memories")
            updated = await client.put(
                f"/api/memories/{memory_id}",
                json={
                    "kind": "correction",
                    "key": "preference:style",
                    "title": "回答偏好",
                    "content": "以后先给结论，再解释依据。",
                },
            )
            rejected = await client.post(
                "/api/memories",
                json={
                    "kind": "profile",
                    "key": "profile:本人:Alice",
                    "title": "本人：Alice",
                    "content": "出生1995-05-12",
                },
            )
            deleted = await client.delete(f"/api/memories/{memory_id}")
            after_delete = await client.get("/api/memories")

        assert created.status_code == 201
        assert listed.json()["memories"][0]["content"] == "以后先给结论。"
        assert updated.status_code == 200
        assert updated.json()["memory"]["kind"] == "correction"
        assert rejected.status_code == 422
        assert deleted.status_code == 200
        assert after_delete.json()["memories"] == []

    asyncio.run(run_test())


def test_authenticated_memory_rejects_client_id_and_isolates_users(memory_api_db):
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as alice:
            await _register(alice, "Alice")
            await alice.post(
                "/api/memories",
                json={
                    "kind": "note",
                    "key": "context:goal",
                    "title": "目标",
                    "content": "Alice 的目标",
                },
            )

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as bob:
            await _register(bob, "Bob")
            legacy_response = await bob.get("/api/memories", params={"client_id": "user:1"})
            response = await bob.get("/api/memories")

        assert legacy_response.status_code == 422
        assert response.status_code == 200
        assert response.json()["memories"] == []

    asyncio.run(run_test())
