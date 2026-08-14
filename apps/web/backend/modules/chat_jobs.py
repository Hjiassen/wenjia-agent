"""Detached Agent jobs that survive the lifetime of an SSE subscriber."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from apps.web.backend.modules import conversation_store
from wenjia_agent.runtime.stream_runner import stream_agent_events

DONE = object()
JobEvent = dict[str, Any]
JobKey = tuple[int, str]


@dataclass
class ChatJob:
    user_id: int
    session_id: str
    effective_user_id: str
    message: str
    run_options: dict[str, Any]
    candidate_suggestions: list[dict[str, Any]]
    task: asyncio.Task[None] | None = None
    history: list[JobEvent] = field(default_factory=list)
    subscribers: set[asyncio.Queue[JobEvent | object]] = field(default_factory=set)
    cancel_requested: bool = False
    done: bool = False


_jobs: dict[JobKey, ChatJob] = {}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _key(user_id: int, session_id: str) -> JobKey:
    return user_id, session_id


def is_running(user_id: int, session_id: str) -> bool:
    job = _jobs.get(_key(user_id, session_id))
    return bool(job and not job.done and job.task and not job.task.done())


def start(
    *,
    user_id: int,
    session_id: str,
    effective_user_id: str,
    message: str,
    run_options: dict[str, Any],
    candidate_suggestions: list[dict[str, Any]],
) -> ChatJob:
    key = _key(user_id, session_id)
    if is_running(user_id, session_id):
        raise RuntimeError("该对话已有推演正在进行。")

    job = ChatJob(
        user_id=user_id,
        session_id=session_id,
        effective_user_id=effective_user_id,
        message=message,
        run_options=run_options,
        candidate_suggestions=candidate_suggestions,
    )
    _jobs[key] = job
    job.task = asyncio.create_task(_run(job), name=f"wenjia-chat:{user_id}:{session_id}")
    return job


def subscribe(user_id: int, session_id: str) -> asyncio.Queue[JobEvent | object] | None:
    job = _jobs.get(_key(user_id, session_id))
    if job is None:
        return None
    queue: asyncio.Queue[JobEvent | object] = asyncio.Queue()
    for event in job.history:
        queue.put_nowait(event)
    if job.done:
        queue.put_nowait(DONE)
    else:
        job.subscribers.add(queue)
    return queue


def unsubscribe(user_id: int, session_id: str, queue: asyncio.Queue[JobEvent | object]) -> None:
    job = _jobs.get(_key(user_id, session_id))
    if job is not None:
        job.subscribers.discard(queue)


def cancel(user_id: int, session_id: str) -> bool:
    job = _jobs.get(_key(user_id, session_id))
    if job is None or job.done or job.task is None or job.task.done():
        return False
    job.cancel_requested = True
    job.task.cancel()
    return True


async def shutdown() -> None:
    jobs = list(_jobs.values())
    for job in jobs:
        if job.task and not job.task.done():
            job.task.cancel()
    if jobs:
        await asyncio.gather(
            *(job.task for job in jobs if job.task is not None),
            return_exceptions=True,
        )


def _publish(job: ChatJob, event: JobEvent) -> None:
    job.history.append(event)
    for queue in tuple(job.subscribers):
        queue.put_nowait(event)


async def _run(job: ChatJob) -> None:
    assistant_body = ""
    assistant_type = ""
    try:
        async for event in stream_agent_events(
            session_id=job.session_id,
            message=job.message,
            user_id=job.effective_user_id,
            **job.run_options,
        ):
            if event.get("type") == "answer_delta":
                assistant_body += event.get("delta", "")
            elif event.get("type") == "done":
                assistant_body = event.get("content") or assistant_body
                event["candidate_suggestions"] = job.candidate_suggestions
            elif event.get("type") == "error":
                assistant_type = "error"
                assistant_body = event.get("message") or assistant_body or "请求失败。"
            _publish(job, event)
    except asyncio.CancelledError:
        if job.cancel_requested:
            assistant_type = "error"
            assistant_body = "（推演已被手动中止）"
            _publish(
                job,
                {
                    "type": "interrupted",
                    "id": f"{job.session_id}:cancelled",
                    "session_id": job.session_id,
                    "timestamp": _now_iso(),
                    "success": False,
                    "source": "server",
                    "message": "推演已被手动中止。",
                },
            )
        else:
            assistant_type = "error"
            assistant_body = "（推演因意外中断而失败）"
            _publish(
                job,
                {
                    "type": "error",
                    "id": f"{job.session_id}:unexpected-cancel",
                    "session_id": job.session_id,
                    "timestamp": _now_iso(),
                    "success": False,
                    "source": "server",
                    "message": "推演因意外中断而失败，请重试。",
                },
            )
    except Exception as exc:  # noqa: BLE001 - detached task boundary.
        assistant_type = "error"
        assistant_body = f"请求失败：{exc}"
        _publish(
            job,
            {
                "type": "error",
                "id": f"{job.session_id}:error",
                "session_id": job.session_id,
                "timestamp": _now_iso(),
                "success": False,
                "source": "server",
                "message": assistant_body,
            },
        )
    finally:
        if not assistant_body:
            assistant_body = "（生成未完成）"
            assistant_type = "error"
        flow = [
            event
            for event in job.history
            if event.get("type") not in {"answer_delta", "answer_reset"}
        ]
        try:
            conversation_store.append_message(
                job.user_id,
                job.session_id,
                "assistant",
                assistant_body,
                payload={
                    "flow": flow,
                    "type": assistant_type,
                    "candidateSuggestions": job.candidate_suggestions if not assistant_type else [],
                },
            )
        finally:
            job.done = True
            for queue in tuple(job.subscribers):
                queue.put_nowait(DONE)
            job.subscribers.clear()
            _jobs.pop(_key(job.user_id, job.session_id), None)
