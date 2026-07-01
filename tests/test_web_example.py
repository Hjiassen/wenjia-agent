import asyncio

import httpx

from apps.web.backend.main import app


def test_web_health():
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            health_response = await client.get("/health")

        assert health_response.json() == {"ok": True}

    asyncio.run(run_test())


def test_web_chat_stream_uses_agent_stream(monkeypatch):
    async def fake_stream_agent_events(session_id: str, message: str):
        assert session_id == "web:test-stream"
        assert "事业" in message
        yield {
            "type": "run_start",
            "session_id": session_id,
            "message": "开始处理请求。",
        }
        yield {
            "type": "tool_start",
            "session_id": session_id,
            "tool": "validate_birth_info_tool",
            "display_name": "出生信息完整性检查",
        }
        yield {
            "type": "done",
            "session_id": session_id,
            "success": True,
            "content": "fake streamed output",
        }

    async def run_test() -> None:
        monkeypatch.setattr(
            "apps.web.backend.api.chat.stream_agent_events", fake_stream_agent_events
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/api/chat/stream",
                json={"session_id": "web:test-stream", "message": "事业怎么样"},
            ) as response:
                body = (await response.aread()).decode("utf-8")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert "data: " in body
        assert "出生信息完整性检查" in body
        assert "fake streamed output" in body

    asyncio.run(run_test())


def test_web_profiles_endpoint(monkeypatch):
    async def run_test() -> None:
        monkeypatch.setattr(
            "apps.web.backend.api.profiles.profile_store.list_profiles",
            lambda _session_id: [
                {
                    "id": 1,
                    "name": "测试",
                    "relationship_type": "本人",
                    "gender": "未知",
                    "pillars": {"year": "乙亥", "month": "辛巳", "day": "甲子", "hour": "己巳"},
                    "five_elements": {"木": 2, "火": 2, "土": 2, "金": 1, "水": 1},
                }
            ],
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/profiles/web:abc")

        assert response.status_code == 200
        payload = response.json()
        assert payload["session_id"] == "web:abc"
        assert payload["profiles"][0]["relationship_type"] == "本人"

    asyncio.run(run_test())


def test_web_profiles_create_and_update(monkeypatch):
    saved: dict[str, object] = {
        "id": 7,
        "name": "测试",
        "relationship_type": "本人",
        "gender": "未知",
        "birth": {"year": 1995},
        "pillars": {"year": None, "month": None, "day": None, "hour": None},
        "five_elements": None,
    }

    def fake_upsert(session_id, data, profile_id=None):
        assert session_id == "web:manual"
        assert data["name"] in {"测试", "测试2"}
        if profile_id is not None:
            assert profile_id == 7
        return {**saved, "name": data["name"]}

    async def run_test() -> None:
        monkeypatch.setattr(
            "apps.web.backend.api.profiles.profile_store.upsert_manual_profile",
            fake_upsert,
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            create_response = await client.post(
                "/api/profiles/web:manual",
                json={"name": "测试", "relationship_type": "本人"},
            )
            update_response = await client.put(
                "/api/profiles/web:manual/7",
                json={"name": "测试2", "relationship_type": "本人"},
            )

        assert create_response.status_code == 200
        assert create_response.json()["profile"]["name"] == "测试"
        assert update_response.status_code == 200
        assert update_response.json()["profile"]["name"] == "测试2"

    asyncio.run(run_test())


def test_web_chat_uses_agent_runner(monkeypatch):
    async def fake_run_agent(session_id: str, message: str) -> str:
        assert session_id == "web:test"
        assert "基础命盘" in message
        return "fake agent output"

    async def run_test() -> None:
        monkeypatch.setattr("apps.web.backend.api.chat.run_agent", fake_run_agent)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/chat",
                json={"session_id": "web:test", "message": "基础命盘"},
            )

        assert response.status_code == 200
        assert response.json() == {"session_id": "web:test", "output": "fake agent output"}

    asyncio.run(run_test())
