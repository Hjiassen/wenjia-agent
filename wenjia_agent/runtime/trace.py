"""Local JSONL tracing for Agent runs.

The OpenAI Agents SDK has its own tracing integration, but local JSONL traces
give this project a provider-independent baseline: every run can be inspected
without external services or credentials.
"""

from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from agents.lifecycle import RunHooksBase
from agents.usage import serialize_usage

from wenjia_agent.runtime.config import settings
from wenjia_agent.runtime.flow_events import get_agent_name, get_tool_name


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _message_preview(message: str, limit: int = 160) -> str:
    compact = " ".join(message.split())
    return compact[:limit]


def _safe_json(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except TypeError:
        return str(value)


@dataclass
class TraceRecorder:
    """Append-only JSONL trace writer for one logical Agent run."""

    run_id: str
    session_id: str
    user_id: str | None
    source: str
    path: Path | None
    started_at: float
    enabled: bool = True

    def emit(self, event_type: str, **fields: Any) -> None:
        if not self.enabled or self.path is None:
            return

        payload = {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "source": self.source,
            "timestamp": _utc_now_iso(),
            "event": event_type,
            **{key: _safe_json(value) for key, value in fields.items()},
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")

    async def aemit(self, event: dict[str, Any]) -> None:
        self.emit("harness_event", **event)

    @contextmanager
    def span(self, name: str, **fields: Any) -> Iterator[None]:
        started = time.perf_counter()
        self.emit("span_start", name=name, **fields)
        try:
            yield
        except Exception as exc:
            self.emit(
                "span_error",
                name=name,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                error_type=exc.__class__.__name__,
                error=str(exc),
            )
            raise
        else:
            self.emit(
                "span_end",
                name=name,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )

    def record_usage(self, usage: Any, *, stage: str, model: str | None = None) -> None:
        if usage is None:
            return
        try:
            serialized = serialize_usage(usage)
        except Exception:  # noqa: BLE001 - tracing must never break a run.
            serialized = str(usage)
        self.emit("usage", stage=stage, model=model, usage=serialized)

    def finish(self, status: str, **fields: Any) -> None:
        self.emit(
            "run_end",
            status=status,
            duration_ms=round((time.perf_counter() - self.started_at) * 1000, 2),
            **fields,
        )


def start_trace(
    session_id: str,
    message: str,
    *,
    source: str,
    user_id: str | None = None,
) -> TraceRecorder:
    """Create and initialize a trace recorder for one run."""

    run_id = uuid.uuid4().hex
    enabled = settings.trace_enabled
    path = None
    if enabled:
        date = datetime.now(UTC).strftime("%Y%m%d")
        path = Path(settings.trace_dir) / f"{date}-{run_id}.jsonl"

    trace = TraceRecorder(
        run_id=run_id,
        session_id=session_id,
        user_id=user_id,
        source=source,
        path=path,
        started_at=time.perf_counter(),
        enabled=enabled,
    )
    trace.emit(
        "run_start",
        message_preview=_message_preview(message),
        agent_model=settings.openai_agent_model,
        analysis_model=settings.openai_analysis_model,
        fallback_model=settings.openai_fallback_model or None,
    )
    return trace


class TraceRunHooks(RunHooksBase[Any, Any]):
    """SDK lifecycle hooks that mirror agent/tool flow into local traces."""

    def __init__(self, trace: TraceRecorder) -> None:
        self.trace = trace

    async def on_agent_start(self, context: Any, agent: Any) -> None:
        self.trace.emit("agent_start", agent=get_agent_name(agent))

    async def on_llm_start(
        self,
        context: Any,
        agent: Any,
        system_prompt: str | None,
        input_items: list[Any],
    ) -> None:
        self.trace.emit(
            "llm_start",
            agent=get_agent_name(agent),
            input_items=len(input_items),
            has_system_prompt=bool(system_prompt),
        )

    async def on_handoff(self, context: Any, from_agent: Any, to_agent: Any) -> None:
        self.trace.emit(
            "handoff",
            from_agent=get_agent_name(from_agent),
            to_agent=get_agent_name(to_agent),
        )

    async def on_tool_start(self, context: Any, agent: Any, tool: Any) -> None:
        self.trace.emit(
            "tool_start",
            agent=get_agent_name(agent),
            tool=get_tool_name(context, tool),
        )

    async def on_tool_end(self, context: Any, agent: Any, tool: Any, result: object) -> None:
        self.trace.emit(
            "tool_end",
            agent=get_agent_name(agent),
            tool=get_tool_name(context, tool),
        )

    async def on_agent_end(self, context: Any, agent: Any, output: Any) -> None:
        self.trace.emit("agent_end", agent=get_agent_name(agent), output_type=type(output).__name__)
