from __future__ import annotations

import asyncio

from apps.web.backend.modules import chat_jobs, conversation_store


def test_chat_job_continues_after_sse_subscriber_disconnects(monkeypatch):
    persisted: list[tuple[str, str]] = []

    async def fake_stream_agent_events(**_kwargs):
        yield {"type": "run_start", "session_id": "web:detached"}
        await asyncio.sleep(0.01)
        yield {"type": "answer_delta", "delta": "后台完成"}
        yield {"type": "done", "success": True, "content": "后台完成"}

    def record_message(_user_id, _session_id, role, body, **_kwargs):
        persisted.append((role, body))

    async def run_test() -> None:
        monkeypatch.setattr(chat_jobs, "stream_agent_events", fake_stream_agent_events)
        monkeypatch.setattr(conversation_store, "append_message", record_message)
        job = chat_jobs.start(
            user_id=1,
            session_id="web:detached",
            effective_user_id="user:1",
            message="继续生成",
            run_options={},
            candidate_suggestions=[],
        )
        queue = chat_jobs.subscribe(1, "web:detached")
        assert queue is not None
        assert await queue.get() == {"type": "run_start", "session_id": "web:detached"}

        chat_jobs.unsubscribe(1, "web:detached", queue)
        await job.task

        assert persisted[-1] == ("assistant", "后台完成")
        assert not chat_jobs.is_running(1, "web:detached")

    asyncio.run(run_test())
