import asyncio

import httpx

from examples.web.app import app


def test_web_index_and_health():
    async def run_test() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            index_response = await client.get("/")
            health_response = await client.get("/health")
            markdown_response = await client.get("/static/markdown.js")

        assert index_response.status_code == 200
        assert "问甲 Agent" in index_response.text
        assert "推荐问题" in index_response.text
        assert "历史记录" in index_response.text
        assert "推演流程" in index_response.text
        assert "/static/markdown.js" in index_response.text
        assert health_response.json() == {"ok": True}
        assert markdown_response.status_code == 200
        assert "renderMarkdown" in markdown_response.text

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
        monkeypatch.setattr("examples.web.app.stream_agent_events", fake_stream_agent_events)
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
