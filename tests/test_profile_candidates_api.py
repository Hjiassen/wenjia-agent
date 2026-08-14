from __future__ import annotations

import asyncio

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.web.backend.main import app
from apps.web.backend.modules import auth_store, profile_candidate_store, profile_store


@pytest.fixture()
def account_db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'candidates.db'}", future=True)
    factory = sessionmaker(bind=engine, future=True)
    for store in (auth_store, profile_store, profile_candidate_store):
        monkeypatch.setattr(store, "_engine", engine)
        monkeypatch.setattr(store, "_Session", factory)
        monkeypatch.setattr(store, "_initialized", False)
    auth_store.init_db()
    profile_store.init_db()
    profile_candidate_store.init_db()
    return engine


async def _register(client: httpx.AsyncClient, username: str) -> None:
    response = await client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "secure-pass-123",
            "confirm_password": "secure-pass-123",
        },
    )
    assert response.status_code == 201


def test_candidate_deduplicates_and_can_convert(account_db):
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await _register(client, "Alice")
            payload = {
                "display_name": "小王",
                "suggested_relationship": "同事",
                "source_session_id": "web:one",
                "source_message_id": "message-1",
            }
            first = await client.post("/api/profile-candidates", json=payload)
            duplicate = await client.post("/api/profile-candidates", json=payload)
            listed = await client.get("/api/profile-candidates")
            candidate_id = first.json()["candidate"]["id"]
            converted = await client.post(
                f"/api/profile-candidates/{candidate_id}/convert",
                json={
                    "name": "小王",
                    "relationship_type": "其他",
                    "custom_relationship": "同事",
                },
            )
            pending_after = await client.get("/api/profile-candidates")

        assert first.status_code == 201
        assert duplicate.status_code == 201
        assert duplicate.json()["candidate"]["id"] == candidate_id
        assert len(listed.json()["candidates"]) == 1
        assert converted.status_code == 201
        assert converted.json()["candidate"]["status"] == "converted"
        assert converted.json()["profile"]["custom_relationship"] == "同事"
        assert pending_after.json()["candidates"] == []

    asyncio.run(run_test())


def test_candidate_ownership_and_dismiss(account_db):
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as alice:
            await _register(alice, "Alice")
            created = await alice.post(
                "/api/profile-candidates",
                json={"display_name": "小李", "suggested_relationship": "朋友"},
            )
            candidate_id = created.json()["candidate"]["id"]
            dismissed = await alice.post(
                f"/api/profile-candidates/{candidate_id}/dismiss"
            )

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as bob:
            await _register(bob, "Bob")
            forbidden = await bob.put(
                f"/api/profile-candidates/{candidate_id}",
                json={"display_name": "修改", "relationship_type": "朋友"},
            )

        assert dismissed.status_code == 200
        assert dismissed.json()["candidate"]["status"] == "dismissed"
        assert forbidden.status_code == 404

    asyncio.run(run_test())


def test_failed_candidate_conversion_keeps_candidate_pending(account_db):
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await _register(client, "Alice")
            existing = await client.post(
                "/api/profiles",
                json={"name": "Alice", "relationship_type": "本人"},
            )
            created = await client.post(
                "/api/profile-candidates",
                json={"display_name": "候选本人", "suggested_relationship": "本人"},
            )
            candidate_id = created.json()["candidate"]["id"]
            converted = await client.post(
                f"/api/profile-candidates/{candidate_id}/convert",
                json={"name": "另一个本人", "relationship_type": "本人"},
            )
            candidates = await client.get("/api/profile-candidates")
            profiles = await client.get("/api/profiles")

        assert existing.status_code == 201
        assert converted.status_code == 409
        assert [item["id"] for item in candidates.json()["candidates"]] == [candidate_id]
        assert [item["name"] for item in profiles.json()["profiles"]] == ["Alice"]

    asyncio.run(run_test())
