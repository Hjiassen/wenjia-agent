import asyncio

import httpx

from examples.web.app import app


def test_web_index_and_health():
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            index_response = await client.get("/")
            health_response = await client.get("/health")

        assert index_response.status_code == 200
        assert "问甲 Agent" in index_response.text
        assert "推荐问题" in index_response.text
        assert "历史记录" in index_response.text
        assert health_response.json() == {"ok": True}

    asyncio.run(run_test())


def test_web_chat_uses_agent_runner(monkeypatch):
    async def fake_run_agent(session_id: str, message: str) -> str:
        assert session_id == "web:test"
        assert "基础命盘" in message
        return "fake agent output"

    async def run_test() -> None:
        monkeypatch.setattr("examples.web.app.run_agent", fake_run_agent)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/chat",
                json={"session_id": "web:test", "message": "基础命盘"},
            )

        assert response.status_code == 200
        assert response.json() == {"session_id": "web:test", "output": "fake agent output"}

    asyncio.run(run_test())
