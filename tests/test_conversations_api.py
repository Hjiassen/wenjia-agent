from __future__ import annotations

import asyncio

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.web.backend.main import app
from apps.web.backend.modules import auth_store, conversation_store


@pytest.fixture()
def conversation_db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'conversations.db'}", future=True)
    factory = sessionmaker(bind=engine, future=True)
    for store in (auth_store, conversation_store):
        monkeypatch.setattr(store, "_engine", engine)
        monkeypatch.setattr(store, "_Session", factory)
        monkeypatch.setattr(store, "_initialized", False)
    auth_store.init_db()
    conversation_store.init_db()


async def register(client: httpx.AsyncClient, username: str) -> None:
    response = await client.post(
        "/api/auth/register",
        json={"username": username, "password": "secure-pass-123", "confirm_password": "secure-pass-123"},
    )
    assert response.status_code == 201


def test_conversations_are_server_owned_and_account_isolated(conversation_db, monkeypatch):
    async def fake_run_agent(**_kwargs):
        return "服务端保存的回答"

    async def run_test() -> None:
        monkeypatch.setattr("apps.web.backend.api.chat.run_agent", fake_run_agent)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as first:
            await register(first, "first-user")
            created = await first.post(
                "/api/chat",
                json={"session_id": "web:server-owned", "message": "请保存这轮对话", "profile_ids": []},
            )
            assert created.status_code == 200

            listing = await first.get("/api/conversations")
            assert listing.status_code == 200
            assert listing.json()["conversations"][0]["id"] == "web:server-owned"

            detail = await first.get("/api/conversations/web:server-owned")
            assert detail.status_code == 200
            assert [item["body"] for item in detail.json()["conversation"]["messages"]] == [
                "请保存这轮对话",
                "服务端保存的回答",
            ]

            async with httpx.AsyncClient(transport=transport, base_url="http://test") as second:
                await register(second, "second-user")
                assert (await second.get("/api/conversations/web:server-owned")).status_code == 404
                assert (await second.delete("/api/conversations/web:server-owned")).status_code == 404

            deleted = await first.delete("/api/conversations/web:server-owned")
            assert deleted.status_code == 200
            assert (await first.get("/api/conversations/web:server-owned")).status_code == 404

    asyncio.run(run_test())
