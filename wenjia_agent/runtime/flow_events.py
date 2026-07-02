"""Agent flow event helpers for web visualization."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

AGENT_DISPLAY_NAMES = {
    "WenjiaMainAgent": "主控路由",
    "ProfileAgent": "出生资料与排盘",
    "FortuneAgent": "命格分析",
    "RelationshipAgent": "关系合盘",
    "NamingAgent": "起名建议",
    "MysticToolsAgent": "工具查询",
}

TOOL_DISPLAY_NAMES = {
    "validate_birth_info": "出生信息完整性检查",
    "validate_birth_info_tool": "出生信息完整性检查",
    "calculate_bazi": "确定性八字排盘",
    "calculate_bazi_tool": "确定性八字排盘",
    "build_bazi_context": "命盘上下文构建",
    "build_bazi_context_tool": "命盘上下文构建",
    "build_luck_cycle_context": "大运流年推算",
    "build_luck_cycle_context_tool": "大运流年推算",
    "save_profile_tool": "人物档案保存",
    "list_profiles_tool": "人物档案查询",
    "list_long_term_memories_tool": "长期记忆查询",
    "list_provinces": "支持省份查询",
    "list_provinces_tool": "支持省份查询",
    "list_cities": "支持城市查询",
    "list_cities_tool": "支持城市查询",
}


def utc_now_iso() -> str:
    """Return an ISO timestamp suitable for SSE payloads."""

    return datetime.now(UTC).isoformat()


def get_agent_name(agent: Any) -> str:
    """Extract a stable Agent name without depending on a concrete SDK class."""

    value = getattr(agent, "name", None)
    return value if isinstance(value, str) and value else agent.__class__.__name__


def get_agent_display_name(agent_or_name: Any) -> str:
    """Return a user-facing Chinese Agent label."""

    name = agent_or_name if isinstance(agent_or_name, str) else get_agent_name(agent_or_name)
    return AGENT_DISPLAY_NAMES.get(name, name)


def get_tool_name(context: Any, tool: Any) -> str:
    """Extract the invoked tool name from SDK context or tool metadata."""

    context_name = getattr(context, "tool_name", None)
    if isinstance(context_name, str) and context_name:
        return context_name

    tool_name = getattr(tool, "name", None)
    if isinstance(tool_name, str) and tool_name:
        return tool_name

    return tool.__class__.__name__


def get_tool_display_name(tool_or_name: Any) -> str:
    """Return a user-facing Chinese tool label."""

    name = tool_or_name if isinstance(tool_or_name, str) else getattr(tool_or_name, "name", "")
    return TOOL_DISPLAY_NAMES.get(name, "工具调用")


def is_tool_result_success(result: object) -> bool:
    """Infer success from a tool result without exposing tool payload details."""

    if isinstance(result, dict):
        if "error" in result:
            return False
        return True

    if isinstance(result, str):
        import json

        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            return True
        return is_tool_result_success(parsed)

    return True


def compact_error_message(exc: Exception) -> str:
    """Normalize exceptions into short messages for browser display."""

    text = str(exc).strip()
    return text or exc.__class__.__name__
