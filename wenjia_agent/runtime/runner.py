"""Runner helpers for wenjia-agent."""

from __future__ import annotations

import asyncio

from agents import Runner
from agents.exceptions import InputGuardrailTripwireTriggered, MaxTurnsExceeded
from agents.extensions.memory import SQLAlchemySession

from wenjia_agent.agents.main_agent import main_agent
from wenjia_agent.guardrails.input_checks import input_check_from_tripwire, run_input_checks
from wenjia_agent.guardrails.output_checks import run_output_checks
from wenjia_agent.harness.loop import ActOutcome, run_harness
from wenjia_agent.harness.policy import HarnessPolicy, default_policy
from wenjia_agent.runtime import memory_store
from wenjia_agent.runtime import profile_store
from wenjia_agent.runtime.config import settings
from wenjia_agent.runtime.models import build_run_config
from wenjia_agent.runtime.output_format import format_final_output
from wenjia_agent.runtime.run_context import WenjiaRunContext
from wenjia_agent.runtime.session_memory import build_session_settings
from wenjia_agent.runtime.trace import TraceRecorder, TraceRunHooks, start_trace

_MAX_TURNS_MESSAGE = "推演步骤过多已中止，请补充更完整的信息或简化问题后重试。"


async def run_agent(session_id: str, message: str, user_id: str | None = None) -> str:
    """Run the main Agent through the harness loop with session memory."""

    policy = default_policy()
    trace = start_trace(session_id, message, source="runtime", user_id=user_id)
    input_check = run_input_checks(message)
    if input_check.blocked:
        trace.emit("input_guardrail", blocked=True, **input_check.to_trace_payload())
        trace.finish("blocked", guardrail="input")
        return input_check.response or "这个请求无法按当前安全边界处理。"

    selected_memories = memory_store.list_memories(user_id, query=message)
    memory_context = memory_store.format_memory_items(selected_memories)
    if memory_context:
        trace.emit(
            "memory_context",
            injected=True,
            item_count=len(selected_memories),
            query_ranked=True,
        )

    try:
        result = await _run_agent_once(
            session_id,
            message,
            policy,
            trace,
            user_id=user_id,
            memory_context=memory_context,
            model_override=None,
        )
        trace.finish("success", fallback_used=False)
        return result.rendered_text
    except InputGuardrailTripwireTriggered as exc:
        input_check = input_check_from_tripwire(exc)
        trace.emit(
            "input_guardrail",
            blocked=True,
            guardrail_source="sdk",
            **input_check.to_trace_payload(),
        )
        trace.finish("blocked", guardrail="input", guardrail_source="sdk")
        return input_check.response or "这个请求无法按当前安全边界处理。"
    except MaxTurnsExceeded:
        trace.finish("max_turns", fallback_used=False)
        return _MAX_TURNS_MESSAGE
    except Exception as exc:
        if not policy.fallback_model:
            trace.finish(
                "error",
                fallback_used=False,
                error_type=exc.__class__.__name__,
                error=str(exc),
            )
            raise

        trace.emit(
            "fallback_start",
            model=policy.fallback_model,
            reason_type=exc.__class__.__name__,
            reason=str(exc),
        )
        try:
            result = await _run_agent_once(
                session_id,
                message,
                policy,
                trace,
                user_id=user_id,
                memory_context=memory_context,
                model_override=policy.fallback_model,
            )
        except InputGuardrailTripwireTriggered as fallback_guardrail_exc:
            input_check = input_check_from_tripwire(fallback_guardrail_exc)
            trace.emit(
                "input_guardrail",
                blocked=True,
                guardrail_source="sdk",
                **input_check.to_trace_payload(),
            )
            trace.finish("blocked", guardrail="input", guardrail_source="sdk", fallback_used=True)
            return input_check.response or "这个请求无法按当前安全边界处理。"
        except MaxTurnsExceeded:
            trace.finish("max_turns", fallback_used=True)
            return _MAX_TURNS_MESSAGE
        except Exception as fallback_exc:
            trace.finish(
                "error",
                fallback_used=True,
                error_type=fallback_exc.__class__.__name__,
                error=str(fallback_exc),
            )
            raise fallback_exc from exc

        trace.finish("success", fallback_used=True)
        return result.rendered_text


async def _run_agent_once(
    session_id: str,
    message: str,
    policy: HarnessPolicy,
    trace: TraceRecorder,
    *,
    user_id: str | None,
    memory_context: str,
    model_override: str | None,
):
    session = SQLAlchemySession.from_url(
        session_id=session_id,
        url=settings.session_db_url,
        create_tables=True,
        session_settings=build_session_settings(),
    )
    context = WenjiaRunContext(
        session_id=session_id,
        user_id=user_id,
        memory_context=memory_context,
    )
    hooks = TraceRunHooks(trace)

    async def act(correction: str | None) -> ActOutcome:
        with trace.span("act", correction=correction is not None, model_override=model_override):
            result = await asyncio.wait_for(
                Runner.run(
                    main_agent,
                    correction or message,
                    session=session,
                    context=context,
                    max_turns=policy.max_turns,
                    hooks=hooks,
                    run_config=build_run_config(model_override, memory_context=memory_context),
                ),
                timeout=policy.model_timeout_seconds,
            )
        trace.record_usage(
            getattr(result.context_wrapper, "usage", None),
            stage="act",
            model=model_override,
        )
        return ActOutcome(result.final_output, format_final_output(result.final_output))

    def verify(outcome: ActOutcome):
        return run_output_checks(
            outcome.rendered_text,
            outcome.final_output,
            profile_store.list_profiles(session_id),
        )

    return await run_harness(act, verify, policy, on_event=trace.aemit)
