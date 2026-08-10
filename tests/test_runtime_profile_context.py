from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.web.backend.api import chat as chat_api
from apps.web.backend.main import app
from apps.web.backend.modules import auth_store
from apps.web.backend.modules import profile_store as account_profile_store
from wenjia_agent.runtime.run_context import WenjiaRunContext
from wenjia_agent.tools import bazi_tools


def test_authenticated_chat_uses_cookie_identity_and_selected_profiles(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'chat.db'}", future=True)
    factory = sessionmaker(bind=engine, future=True)
    monkeypatch.setattr(auth_store, "_engine", engine)
    monkeypatch.setattr(auth_store, "_Session", factory)
    monkeypatch.setattr(auth_store, "_initialized", False)
    monkeypatch.setattr(account_profile_store, "_engine", engine)
    monkeypatch.setattr(account_profile_store, "_Session", factory)
    monkeypatch.setattr(account_profile_store, "_initialized", False)
    auth_store.init_db()
    account_profile_store.init_db()

    async def run_test() -> None:
        captured: dict = {}

        async def fake_run_agent(**kwargs):
            captured.update(kwargs)
            return "ok"

        monkeypatch.setattr(chat_api, "run_agent", fake_run_agent)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/auth/register",
                json={"username": "ChatUser", "password": "secure-pass-123", "confirm_password": "secure-pass-123"},
            )
            created = await client.post(
                "/api/profiles",
                json={"name": "本人", "relationship_type": "本人"},
            )
            profile_id = created.json()["profile"]["id"]
            response = await client.post(
                "/api/chat",
                json={
                    "message": "看一下",
                    "session_id": "web:chat-test",
                    "profile_ids": [profile_id],
                },
            )

        assert response.status_code == 200
        assert captured["user_id"].startswith("user:")
        assert captured["profile_context"][0]["id"] == profile_id
        assert callable(captured["profile_writer"])

    asyncio.run(run_test())


def test_authenticated_chat_rejects_legacy_client_id(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy-chat.db'}", future=True)
    factory = sessionmaker(bind=engine, future=True)
    monkeypatch.setattr(auth_store, "_engine", engine)
    monkeypatch.setattr(auth_store, "_Session", factory)
    monkeypatch.setattr(auth_store, "_initialized", False)
    auth_store.init_db()

    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/auth/register",
                json={"username": "LegacyUser", "password": "secure-pass-123", "confirm_password": "secure-pass-123"},
            )
            response = await client.post(
                "/api/chat",
                json={"message": "测试", "client_id": "client:legacy"},
            )
        assert response.status_code == 422

    asyncio.run(run_test())


def test_list_profiles_prefers_explicit_account_profiles():
    profiles = [{"id": 9, "name": "账号档案", "relationship_type": "本人"}]
    result = bazi_tools._list_profiles(WenjiaRunContext(profile_context=profiles))
    assert result["data"]["profiles"] == profiles


def test_autosave_uses_account_profile_writer():
    calls: list[tuple[str, dict, dict]] = []

    def writer(relationship_type: str, bazi: dict, context: dict) -> dict:
        calls.append((relationship_type, bazi, context))
        return {"id": 10, "name": bazi["name"]}

    result = bazi_tools.build_bazi_context_data(
        name="账号人物",
        gender="未知",
        birth_year=1995,
        birth_month=5,
        birth_day=12,
        birth_hour=9,
        birth_minute=30,
        province="北京市",
        city="北京市",
    )
    ctx = SimpleNamespace(
        context=WenjiaRunContext(profile_writer=writer, session_id="web:account")
    )

    bazi_tools._autosave_subject(ctx, result)  # type: ignore[arg-type]

    assert calls
    assert calls[0][0] == "本人"
    assert calls[0][1]["name"] == "账号人物"
