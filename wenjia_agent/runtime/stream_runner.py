"""Streaming Agent runner with visualization events."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

from agents import Runner
from agents.exceptions import InputGuardrailTripwireTriggered, MaxTurnsExceeded
from agents.extensions.memory import SQLAlchemySession
from agents.lifecycle import RunHooksBase
from agents.stream_events import AgentUpdatedStreamEvent, RawResponsesStreamEvent
from openai.types.responses.response_text_delta_event import ResponseTextDeltaEvent

from wenjia_agent.agents.main_agent import main_agent
from wenjia_agent.guardrails.input_checks import input_check_from_tripwire, run_input_checks
from wenjia_agent.guardrails.output_checks import run_output_checks
from wenjia_agent.harness.loop import ActOutcome, run_harness
from wenjia_agent.harness.policy import default_policy
from wenjia_agent.runtime import memory_store, profile_store
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
from wenjia_agent.runtime.trace import TraceRecorder, start_trace

FlowEvent = dict[str, Any]
_QUEUE_SENTINEL = object()
_MAX_TURNS_MESSAGE = "推演步骤过多已中止，请补充更完整的信息或简化问题后重试。"
_ANSWER_CHUNK_WIDTH = 28
_ANSWER_CHUNK_DELAY_SECONDS = 0.012


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

    def __init__(self, emitter: FlowEventEmitter, trace: TraceRecorder) -> None:
        self.emitter = emitter
        self.trace = trace
        self._tool_started_at: dict[str, float] = {}

    async def on_agent_start(self, context: Any, agent: Any) -> None:
        agent_name = get_agent_name(agent)
        agent_label = get_agent_display_name(agent_name)
        self.trace.emit("agent_start", agent=agent_name)
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
        self.trace.emit(
            "llm_start",
            agent=agent_name,
            input_items=len(input_items),
            has_system_prompt=bool(system_prompt),
        )
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
        self.trace.emit("handoff", from_agent=from_name, to_agent=to_name)
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
        self.trace.emit("tool_start", agent=get_agent_name(agent), tool=tool_name)
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
        self.trace.emit(
            "tool_end",
            agent=get_agent_name(agent),
            tool=tool_name,
            duration=duration,
            success=success,
        )
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
        self.trace.emit("agent_end", agent=agent_name, output_type=type(output).__name__)
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


def _display_width(char: str) -> int:
    return 2 if ord(char) > 127 else 1


def _iter_answer_chunks(text: str) -> AsyncIterator[str]:
    async def chunks() -> AsyncIterator[str]:
        buffer: list[str] = []
        width = 0
        for char in text:
            buffer.append(char)
            width += _display_width(char)
            if char == "\n" or width >= _ANSWER_CHUNK_WIDTH:
                yield "".join(buffer)
                buffer = []
                width = 0
        if buffer:
            yield "".join(buffer)

    return chunks()


def _agent_streams_display_text(agent: Any) -> bool:
    return getattr(agent, "output_type", None) is None


def _text_delta_from_sdk_event(event: Any) -> str:
    if not isinstance(event, RawResponsesStreamEvent):
        return ""
    if isinstance(event.data, ResponseTextDeltaEvent):
        return event.data.delta
    return ""


async def _emit_input_guardrail_response(
    emitter: FlowEventEmitter,
    trace: TraceRecorder,
    input_check: Any,
    *,
    guardrail_source: str,
) -> None:
    trace.emit(
        "input_guardrail",
        blocked=True,
        guardrail_source=guardrail_source,
        **input_check.to_trace_payload(),
    )
    await emitter.emit(
        {
            "type": "input_guardrail",
            "success": True,
            "blocked": True,
            "code": input_check.issues[0].code if input_check.issues else None,
            "category": input_check.issues[0].category if input_check.issues else None,
            "message": input_check.issues[0].message if input_check.issues else "输入护栏已拦截。",
        }
    )
    response_text = input_check.response or "这个请求无法按当前安全边界处理。"
    async for chunk in _iter_answer_chunks(response_text):
        await emitter.emit({"type": "answer_delta", "delta": chunk})
        await asyncio.sleep(_ANSWER_CHUNK_DELAY_SECONDS)
    await emitter.emit(
        {
            "type": "done",
            "success": True,
            "content": response_text,
            "message": "已按安全边界处理。",
        }
    )
    trace.finish("blocked", guardrail="input", guardrail_source=guardrail_source)


async def stream_agent_events(
    session_id: str,
    message: str,
    user_id: str | None = None,
) -> AsyncIterator[FlowEvent]:
    """Run the main Agent and yield normalized flow events."""

    queue: asyncio.Queue[FlowEvent | object] = asyncio.Queue()
    emitter = FlowEventEmitter(session_id=session_id, queue=queue)
    trace = start_trace(session_id, message, source="web_stream", user_id=user_id)
    await emitter.emit({"type": "run_start", "message": "开始处理请求。"})

    input_check = run_input_checks(message)
    if input_check.blocked:
        await _emit_input_guardrail_response(
            emitter,
            trace,
            input_check,
            guardrail_source="precheck",
        )
        while not queue.empty():
            event = await queue.get()
            if event is not _QUEUE_SENTINEL:
                yield event
        return

    memory_context = memory_store.format_memory_context(user_id)
    if memory_context:
        trace.emit(
            "memory_context",
            injected=True,
            item_count=len(memory_store.list_memories(user_id)),
        )

    async def consume_sdk_stream() -> None:
        policy = default_policy()
        streamed_answer = ""

        async def run_with_model(model_override: str | None):
            session = SQLAlchemySession.from_url(
                session_id=session_id,
                url=settings.session_db_url,
                create_tables=True,
            )
            hooks = FlowRunHooks(emitter, trace)
            context = WenjiaRunContext(
                session_id=session_id,
                user_id=user_id,
                memory_context=memory_context,
            )

            async def act(correction: str | None) -> ActOutcome:
                return await run_act(correction, session, context, hooks, model_override)

            def verify(outcome: ActOutcome):
                return run_output_checks(
                    outcome.rendered_text,
                    outcome.final_output,
                    profile_store.list_profiles(session_id),
                )

            async def emit_harness_event(event: FlowEvent) -> None:
                trace.emit("harness_event", **event)
                await emitter.emit(event)

            return await run_harness(act, verify, policy, on_event=emit_harness_event)

        async def run_act(
            correction: str | None,
            session: SQLAlchemySession,
            context: WenjiaRunContext,
            hooks: FlowRunHooks,
            model_override: str | None,
        ) -> ActOutcome:
            nonlocal streamed_answer
            streamed_answer = ""
            if correction is not None:
                await emitter.emit({"type": "answer_reset"})

            with trace.span("act", correction=correction is not None, model_override=model_override):
                result = Runner.run_streamed(
                    main_agent,
                    correction or message,
                    session=session,
                    context=context,
                    max_turns=policy.max_turns,
                    hooks=hooks,
                    run_config=build_run_config(model_override, memory_context=memory_context),
                )
                stream_display_text = _agent_streams_display_text(main_agent)
                try:
                    async with asyncio.timeout(policy.model_timeout_seconds):
                        async for sdk_event in result.stream_events():
                            if isinstance(sdk_event, AgentUpdatedStreamEvent):
                                stream_display_text = _agent_streams_display_text(
                                    sdk_event.new_agent
                                )
                                continue

                            delta = _text_delta_from_sdk_event(sdk_event)
                            if delta and stream_display_text:
                                streamed_answer += delta
                                await emitter.emit(
                                    {
                                        "type": "answer_delta",
                                        "delta": delta,
                                    }
                                )
                except TimeoutError:
                    result.cancel()
                    raise

            run_loop_exception = getattr(result, "run_loop_exception", None)
            if run_loop_exception:
                raise run_loop_exception
            trace.record_usage(
                getattr(result.context_wrapper, "usage", None),
                stage="act",
                model=model_override,
            )
            return ActOutcome(result.final_output, format_final_output(result.final_output))

        try:
            try:
                result = await run_with_model(None)
                fallback_used = False
            except InputGuardrailTripwireTriggered:
                raise
            except MaxTurnsExceeded:
                raise
            except Exception as exc:
                if not policy.fallback_model:
                    raise
                fallback_used = True
                trace.emit(
                    "fallback_start",
                    model=policy.fallback_model,
                    reason_type=exc.__class__.__name__,
                    reason=str(exc),
                )
                await emitter.emit(
                    {
                        "type": "fallback",
                        "success": True,
                        "message": "主模型响应异常，正在切换备用模型。",
                    }
                )
                await emitter.emit({"type": "answer_reset"})
                result = await run_with_model(policy.fallback_model)

            text_to_stream = result.rendered_text
            if streamed_answer and result.rendered_text.startswith(streamed_answer):
                text_to_stream = result.rendered_text[len(streamed_answer):]
            elif streamed_answer:
                await emitter.emit({"type": "answer_reset"})

            async for chunk in _iter_answer_chunks(text_to_stream):
                await emitter.emit(
                    {
                        "type": "answer_delta",
                        "delta": chunk,
                    }
                )
                await asyncio.sleep(_ANSWER_CHUNK_DELAY_SECONDS)
            await emitter.emit(
                {
                    "type": "done",
                    "success": True,
                    "content": result.rendered_text,
                    "message": "推演完成。",
                }
            )
            trace.finish("success", fallback_used=fallback_used)
        except InputGuardrailTripwireTriggered as exc:
            input_check = input_check_from_tripwire(exc)
            await _emit_input_guardrail_response(
                emitter,
                trace,
                input_check,
                guardrail_source="sdk",
            )
        except MaxTurnsExceeded:
            trace.finish("max_turns")
            await emitter.emit(
                {
                    "type": "error",
                    "success": False,
                    "message": _MAX_TURNS_MESSAGE,
                }
            )
        except Exception as exc:  # noqa: BLE001 - stream boundary.
            trace.finish("error", error_type=exc.__class__.__name__, error=str(exc))
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
