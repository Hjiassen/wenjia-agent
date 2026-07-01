"""Streaming Agent runner with visualization events."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

from agents import Runner
from agents.exceptions import MaxTurnsExceeded
from agents.extensions.memory import SQLAlchemySession
from agents.lifecycle import RunHooksBase

from wenjia_agent.agents.main_agent import main_agent
from wenjia_agent.guardrails.output_checks import run_output_checks
from wenjia_agent.harness.loop import ActOutcome, run_harness
from wenjia_agent.harness.policy import default_policy
from wenjia_agent.runtime import profile_store
from wenjia_agent.runtime.config import settings
from wenjia_agent.runtime.output_format import format_final_output
from wenjia_agent.runtime.run_context import WenjiaRunContext
from wenjia_agent.runtime.flow_events import (
    compact_error_message,
    get_agent_display_name,
    get_agent_name,
    get_tool_display_name,
    get_tool_name,
    is_tool_result_success,
    utc_now_iso,
)
from wenjia_agent.runtime.models import build_run_config

FlowEvent = dict[str, Any]
_QUEUE_SENTINEL = object()
_MAX_TURNS_MESSAGE = "推演步骤过多已中止，请补充更完整的信息或简化问题后重试。"


class FlowEventEmitter:
    """Assign common metadata and enqueue events for SSE streaming."""

    def __init__(self, session_id: str, queue: asyncio.Queue[FlowEvent | object]) -> None:
        self.session_id = session_id
        self.queue = queue
        self._sequence = 0

    async def emit(self, event: FlowEvent) -> None:
        self._sequence += 1
        payload = {
            "id": f"{self.session_id}:{self._sequence}",
            "session_id": self.session_id,
            "timestamp": utc_now_iso(),
            **event,
        }
        await self.queue.put(payload)


class FlowRunHooks(RunHooksBase[Any, Any]):
    """Translate OpenAI Agents SDK lifecycle callbacks into UI flow events."""

    def __init__(self, emitter: FlowEventEmitter) -> None:
        self.emitter = emitter
        self._tool_started_at: dict[str, float] = {}

    async def on_agent_start(self, context: Any, agent: Any) -> None:
        agent_name = get_agent_name(agent)
        agent_label = get_agent_display_name(agent_name)
        await self.emitter.emit(
            {
                "type": "agent_start",
                "agent": agent_name,
                "agent_label": agent_label,
                "message": f"{agent_label}开始处理。",
            }
        )

    async def on_llm_start(
        self,
        context: Any,
        agent: Any,
        system_prompt: str | None,
        input_items: list[Any],
    ) -> None:
        agent_name = get_agent_name(agent)
        agent_label = get_agent_display_name(agent_name)
        await self.emitter.emit(
            {
                "type": "thinking",
                "agent": agent_name,
                "agent_label": agent_label,
                "message": f"{agent_label}正在判断下一步。",
            }
        )

    async def on_handoff(self, context: Any, from_agent: Any, to_agent: Any) -> None:
        from_name = get_agent_name(from_agent)
        to_name = get_agent_name(to_agent)
        from_label = get_agent_display_name(from_name)
        to_label = get_agent_display_name(to_name)
        await self.emitter.emit(
            {
                "type": "handoff",
                "from_agent": from_name,
                "to_agent": to_name,
                "from_agent_label": from_label,
                "to_agent_label": to_label,
                "message": f"{from_label}移交给{to_label}。",
            }
        )

    async def on_tool_start(self, context: Any, agent: Any, tool: Any) -> None:
        tool_name = get_tool_name(context, tool)
        tool_call_id = _tool_call_id(context, tool_name)
        display_name = get_tool_display_name(tool_name)
        self._tool_started_at[tool_call_id] = time.perf_counter()
        await self.emitter.emit(
            {
                "type": "tool_start",
                "agent": get_agent_name(agent),
                "agent_label": get_agent_display_name(agent),
                "tool": tool_name,
                "tool_call_id": tool_call_id,
                "display_name": display_name,
                "message": f"正在执行{display_name}。",
            }
        )

    async def on_tool_end(self, context: Any, agent: Any, tool: Any, result: object) -> None:
        tool_name = get_tool_name(context, tool)
        tool_call_id = _tool_call_id(context, tool_name)
        display_name = get_tool_display_name(tool_name)
        started_at = self._tool_started_at.pop(tool_call_id, None)
        duration = round(time.perf_counter() - started_at, 2) if started_at else None
        success = is_tool_result_success(result)
        await self.emitter.emit(
            {
                "type": "tool_done",
                "agent": get_agent_name(agent),
                "agent_label": get_agent_display_name(agent),
                "tool": tool_name,
                "tool_call_id": tool_call_id,
                "display_name": display_name,
                "success": success,
                "duration": duration,
                "message": f"{display_name}{'完成' if success else '失败'}。",
            }
        )

    async def on_agent_end(self, context: Any, agent: Any, output: Any) -> None:
        agent_name = get_agent_name(agent)
        agent_label = get_agent_display_name(agent_name)
        await self.emitter.emit(
            {
                "type": "generating",
                "agent": agent_name,
                "agent_label": agent_label,
                "message": f"{agent_label}正在整理最终回答。",
            }
        )


def _tool_call_id(context: Any, tool_name: str) -> str:
    candidate = getattr(context, "tool_call_id", None)
    if isinstance(candidate, str) and candidate:
        return candidate
    return tool_name


async def stream_agent_events(session_id: str, message: str) -> AsyncIterator[FlowEvent]:
    """Run the main Agent and yield normalized flow events."""

    queue: asyncio.Queue[FlowEvent | object] = asyncio.Queue()
    emitter = FlowEventEmitter(session_id=session_id, queue=queue)
    await emitter.emit({"type": "run_start", "message": "开始处理请求。"})

    async def consume_sdk_stream() -> None:
        session = SQLAlchemySession.from_url(
            session_id=session_id,
            url=settings.session_db_url,
            create_tables=True,
        )
        hooks = FlowRunHooks(emitter)
        context = WenjiaRunContext(session_id=session_id)
        policy = default_policy()

        async def act(correction: str | None) -> ActOutcome:
            result = Runner.run_streamed(
                main_agent,
                correction or message,
                session=session,
                context=context,
                max_turns=policy.max_turns,
                hooks=hooks,
                run_config=build_run_config(),
            )
            async for _event in result.stream_events():
                pass
            if result.run_loop_exception:
                raise result.run_loop_exception
            return ActOutcome(result.final_output, format_final_output(result.final_output))

        def verify(outcome: ActOutcome):
            return run_output_checks(
                outcome.rendered_text,
                outcome.final_output,
                profile_store.list_profiles(session_id),
            )

        try:
            result = await run_harness(act, verify, policy, on_event=emitter.emit)
            await emitter.emit(
                {
                    "type": "done",
                    "success": True,
                    "content": result.rendered_text,
                    "message": "推演完成。",
                }
            )
        except MaxTurnsExceeded:
            await emitter.emit(
                {
                    "type": "error",
                    "success": False,
                    "message": _MAX_TURNS_MESSAGE,
                }
            )
        except Exception as exc:  # noqa: BLE001 - stream boundary.
            await emitter.emit(
                {
                    "type": "error",
                    "success": False,
                    "message": compact_error_message(exc),
                }
            )
        finally:
            await queue.put(_QUEUE_SENTINEL)

    task = asyncio.create_task(consume_sdk_stream())
    try:
        while True:
            event = await queue.get()
            if event is _QUEUE_SENTINEL:
                break
            yield event
    finally:
        if not task.done():
            task.cancel()
