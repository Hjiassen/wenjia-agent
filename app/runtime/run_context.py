"""Run-scoped context shared across Agent turns.

The OpenAI Agents SDK threads a single ``context`` object through every tool
invocation in a run (injected as the first parameter when a tool declares a
``RunContextWrapper``/``ToolContext`` argument). We use it to memoize the
deterministic charting tools so a weak model cannot get stuck calling the same
tool with identical arguments until ``max_turns`` is exceeded.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

REPEAT_TOOL_NOTE = "排盘结果已生成，请直接基于现有结果输出或分析，不要再次调用排盘工具。"


@dataclass
class WenjiaRunContext:
    """Per-run state passed to ``Runner.run`` / ``Runner.run_streamed``."""

    tool_cache: dict[str, dict[str, Any]] = field(default_factory=dict)

    def cache_key(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Build a stable key from a tool name and its normalized arguments."""

        normalized = json.dumps(arguments, sort_keys=True, ensure_ascii=False, default=str)
        return f"{tool_name}:{normalized}"

    def cached_result(self, key: str) -> dict[str, Any] | None:
        """Return a previously computed result, tagged so the model stops looping."""

        previous = self.tool_cache.get(key)
        if previous is None:
            return None
        return {**previous, "note": REPEAT_TOOL_NOTE, "from_cache": True}

    def store_result(self, key: str, result: dict[str, Any]) -> dict[str, Any]:
        """Memoize a freshly computed tool result and return it unchanged."""

        self.tool_cache[key] = result
        return result
