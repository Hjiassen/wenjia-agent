from types import SimpleNamespace

from wenjia_agent.runtime.run_context import REPEAT_TOOL_NOTE, WenjiaRunContext
from wenjia_agent.tools.bazi_tools import _dedup_charting


def test_cache_miss_then_hit_marks_repeat_and_skips_recompute():
    context = WenjiaRunContext()
    args = {"name": "测试", "birth_year": 1995}
    key = context.cache_key("build_bazi_context_tool", args)

    assert context.cached_result(key) is None

    computed = {"ok": True, "tool_name": "build_bazi_context", "data": {"x": 1}}
    stored = context.store_result(key, computed)
    assert stored is computed
    assert "note" not in stored

    cached = context.cached_result(key)
    assert cached is not None
    assert cached["note"] == REPEAT_TOOL_NOTE
    assert cached["from_cache"] is True
    assert cached["data"] == {"x": 1}


def test_cache_key_is_order_independent():
    context = WenjiaRunContext()
    left = context.cache_key("calculate_bazi_tool", {"a": 1, "b": 2})
    right = context.cache_key("calculate_bazi_tool", {"b": 2, "a": 1})
    assert left == right


def test_different_arguments_do_not_collide():
    context = WenjiaRunContext()
    key_one = context.cache_key("build_bazi_context_tool", {"birth_hour": 9})
    key_two = context.cache_key("build_bazi_context_tool", {"birth_hour": 10})
    assert key_one != key_two


def test_dedup_charting_computes_once_then_serves_cache():
    """The loop-breaker: a repeated identical charting call must not recompute."""

    ctx = SimpleNamespace(context=WenjiaRunContext())  # duck-typed RunContextWrapper
    calls = {"count": 0}

    def compute(**kwargs):
        calls["count"] += 1
        return {"ok": True, "echo": kwargs}

    args = {"name": "测试", "birth_year": 1995, "birth_hour": 9}

    first = _dedup_charting(ctx, "build_bazi_context_tool", args, compute)  # type: ignore[arg-type]
    assert calls["count"] == 1
    assert first["ok"] is True
    assert "note" not in first

    second = _dedup_charting(ctx, "build_bazi_context_tool", dict(args), compute)  # type: ignore[arg-type]
    assert calls["count"] == 1  # served from cache, no recompute
    assert second["note"] == REPEAT_TOOL_NOTE
    assert second["from_cache"] is True


def test_dedup_charting_without_run_context_still_computes():
    """When no WenjiaRunContext is present, the tool degrades to a direct call."""

    ctx = SimpleNamespace(context=None)  # duck-typed RunContextWrapper
    calls = {"count": 0}

    def compute(**_kwargs):
        calls["count"] += 1
        return {"ok": True}

    _dedup_charting(ctx, "calculate_bazi_tool", {"a": 1}, compute)  # type: ignore[arg-type]
    _dedup_charting(ctx, "calculate_bazi_tool", {"a": 1}, compute)  # type: ignore[arg-type]
    assert calls["count"] == 2
