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


async def register(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/auth/register",
        json={"username": "webuser", "password": "secure-pass-123", "confirm_password": "secure-pass-123"},
    )
    assert response.status_code == 201


def test_web_health():
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
        assert response.json() == {"ok": True}

    asyncio.run(run_test())


def test_web_requires_login_for_app_endpoints():
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            endpoints = [
                ("POST", "/api/chat", {"message": "测试"}),
                ("POST", "/api/chat/stream", {"message": "测试"}),
                ("POST", "/api/chat/web:test/cancel", None),
                ("POST", "/api/chat/suggestions", {"user_message": "测试", "assistant_message": "回答"}),
                ("GET", "/api/profiles", None),
                ("GET", "/api/profiles/meta/cities", None),
                ("GET", "/api/memories", None),
                ("GET", "/api/conversations", None),
            ]
            responses = [await client.request(method, path, json=body) for method, path, body in endpoints]
        assert all(response.status_code == 401 for response in responses)

    asyncio.run(run_test())


def test_authenticated_chat_forwards_account_identity(monkeypatch, auth_db):
    async def fake_run_agent(**kwargs):
        assert kwargs["user_id"].startswith("user:")
        assert kwargs["profile_context"] == []
        assert callable(kwargs["profile_writer"])
        return "fake agent output"

    async def run_test() -> None:
        monkeypatch.setattr("apps.web.backend.api.chat.run_agent", fake_run_agent)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await register(client)
            response = await client.post(
                "/api/chat",
                json={"session_id": "web:test", "message": "基础命盘", "profile_ids": []},
            )
        assert response.status_code == 200
        assert response.json() == {"session_id": "web:test", "output": "fake agent output"}

    asyncio.run(run_test())


def test_authenticated_city_options_endpoint(auth_db):
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await register(client)
            response = await client.get("/api/profiles/meta/cities")
        assert response.status_code == 200
        payload = response.json()
        beijing = next(item for item in payload["options"] if item["value"] == "北京市")
        assert {"label": "北京市", "value": "北京市"} in beijing["children"]

    asyncio.run(run_test())
