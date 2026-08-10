from __future__ import annotations

import asyncio

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.web.backend.main import app
from apps.web.backend.modules import auth_store, profile_store


@pytest.fixture()
def account_db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'accounts.db'}", future=True)
    factory = sessionmaker(bind=engine, future=True)
    for store in (auth_store, profile_store):
        monkeypatch.setattr(store, "_engine", engine)
        monkeypatch.setattr(store, "_Session", factory)
        monkeypatch.setattr(store, "_initialized", False)
    auth_store.init_db()
    profile_store.init_db()
    return engine


async def _register(client: httpx.AsyncClient, username: str) -> None:
    response = await client.post(
        "/api/auth/register",
        json={"username": username, "password": "secure-pass-123", "confirm_password": "secure-pass-123"},
    )
    assert response.status_code == 201


def test_profile_api_requires_authentication(account_db):
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/profiles")
        assert response.status_code == 401

    asyncio.run(run_test())


def test_profile_crud_soft_delete_and_restore(account_db):
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await _register(client, "Alice")
            created = await client.post(
                "/api/profiles",
                json={
                    "name": "小爱",
                    "relationship_type": "本人",
                    "gender": "女",
                    "birth_year": 1995,
                    "birth_month": 5,
                    "birth_day": 12,
                },
            )
            profile_id = created.json()["profile"]["id"]
            listed = await client.get("/api/profiles")
            updated = await client.put(
                f"/api/profiles/{profile_id}",
                json={"name": "小艾", "relationship_type": "本人", "gender": "女"},
            )
            deleted = await client.delete(f"/api/profiles/{profile_id}")
            active_after_delete = await client.get("/api/profiles")
            recycle_bin = await client.get("/api/profiles/deleted")
            restore = await client.post(f"/api/profiles/{profile_id}/restore")

        assert created.status_code == 201
        assert listed.json()["profiles"][0]["name"] == "小爱"
        assert updated.json()["profile"]["name"] == "小艾"
        assert deleted.status_code == 200
        assert deleted.json()["profile"]["deleted_at"] is not None
        assert active_after_delete.json()["profiles"] == []
        assert recycle_bin.json()["profiles"][0]["id"] == profile_id
        assert restore.status_code == 200
        assert restore.json()["profile"]["deleted_at"] is None

    asyncio.run(run_test())


def test_profile_ownership_returns_not_found(account_db):
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as alice:
            await _register(alice, "Alice")
            created = await alice.post(
                "/api/profiles",
                json={"name": "Alice", "relationship_type": "本人"},
            )
            profile_id = created.json()["profile"]["id"]

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as bob:
            await _register(bob, "Bob")
            read_response = await bob.get(f"/api/profiles/{profile_id}")
            update_response = await bob.put(
                f"/api/profiles/{profile_id}",
                json={"name": "stolen", "relationship_type": "朋友"},
            )
            delete_response = await bob.delete(f"/api/profiles/{profile_id}")

        assert read_response.status_code == 404
        assert update_response.status_code == 404
        assert delete_response.status_code == 404

    asyncio.run(run_test())


def test_only_one_active_self_profile_and_restore_checks_conflict(account_db):
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await _register(client, "Alice")
            first = await client.post(
                "/api/profiles",
                json={"name": "Alice", "relationship_type": "本人"},
            )
            duplicate = await client.post(
                "/api/profiles",
                json={"name": "Alice 2", "relationship_type": "本人"},
            )
            await client.delete(f"/api/profiles/{first.json()['profile']['id']}")
            replacement = await client.post(
                "/api/profiles",
                json={"name": "Alice 2", "relationship_type": "本人"},
            )
            restore = await client.post(
                f"/api/profiles/{first.json()['profile']['id']}/restore",
            )

        assert duplicate.status_code == 409
        assert replacement.status_code == 201
        assert restore.status_code == 409

    asyncio.run(run_test())
