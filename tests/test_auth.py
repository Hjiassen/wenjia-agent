from __future__ import annotations

import asyncio

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.web.backend.main import app
from apps.web.backend.modules import auth_store


@pytest.fixture()
def auth_db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'auth.db'}", future=True)
    monkeypatch.setattr(auth_store, "_engine", engine)
    monkeypatch.setattr(auth_store, "_Session", sessionmaker(bind=engine, future=True))
    monkeypatch.setattr(auth_store, "_initialized", False)
    auth_store.init_db()
    return engine


def test_register_sets_session_cookie_and_returns_current_user(auth_db):
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/register",
                json={"username": "TestUser", "password": "secure-pass-123", "confirm_password": "secure-pass-123"},
            )
            me_response = await client.get("/api/auth/me")

        assert response.status_code == 201
        assert response.json()["user"]["username"] == "TestUser"
        cookie_header = response.headers["set-cookie"]
        assert "HttpOnly" in cookie_header
        assert "samesite=lax" in cookie_header.lower()
        assert me_response.status_code == 200
        assert me_response.json()["user"]["username"] == "TestUser"

        user = auth_store.get_user_by_username("testuser")
        assert user is not None
        assert user["password_hash"].startswith("$argon2id$")
        assert user["password_hash"] != "secure-pass-123"

    asyncio.run(run_test())


def test_username_uniqueness_is_case_insensitive(auth_db):
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post(
                "/api/auth/register",
                json={"username": "Alice", "password": "secure-pass-123", "confirm_password": "secure-pass-123"},
            )
            second = await client.post(
                "/api/auth/register",
                json={"username": "alice", "password": "another-pass-123", "confirm_password": "another-pass-123"},
            )

        assert first.status_code == 201
        assert second.status_code == 409

    asyncio.run(run_test())


def test_login_uses_generic_invalid_credentials_error(auth_db):
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/auth/register",
                json={"username": "Alice", "password": "secure-pass-123", "confirm_password": "secure-pass-123"},
            )
            await client.post("/api/auth/logout")
            unknown = await client.post(
                "/api/auth/login",
                json={"username": "unknown", "password": "wrong-pass"},
            )
            wrong_password = await client.post(
                "/api/auth/login",
                json={"username": "Alice", "password": "wrong-pass"},
            )

        assert unknown.status_code == 401
        assert wrong_password.status_code == 401
        assert unknown.json()["detail"] == wrong_password.json()["detail"]

    asyncio.run(run_test())


def test_logout_revokes_current_session(auth_db):
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/auth/register",
                json={"username": "Alice", "password": "secure-pass-123", "confirm_password": "secure-pass-123"},
            )
            logout = await client.post("/api/auth/logout")
            me_response = await client.get("/api/auth/me")

        assert logout.status_code == 200
        assert me_response.status_code == 401

    asyncio.run(run_test())


def test_register_requires_matching_password_confirmation(auth_db):
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            missing = await client.post(
                "/api/auth/register",
                json={"username": "Alice", "password": "secure-pass-123"},
            )
            mismatch = await client.post(
                "/api/auth/register",
                json={
                    "username": "Alice",
                    "password": "secure-pass-123",
                    "confirm_password": "different-pass-123",
                },
            )

        assert missing.status_code == 422
        assert mismatch.status_code == 422

    asyncio.run(run_test())
