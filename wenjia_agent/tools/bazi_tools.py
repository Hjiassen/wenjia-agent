"""OpenAI Agents SDK tools for deterministic BaZi calculation."""

from __future__ import annotations

from agents import RunContextWrapper, function_tool

from wenjia_agent.core.city_data import get_cities, get_provinces
from wenjia_agent.domain.context_builders import build_bazi_context
from wenjia_agent.domain.bazi_adapter import BaziAdapter
from wenjia_agent.domain.schemas import BaziResult, BirthInfo, ToolResult
from wenjia_agent.runtime import memory_store
from wenjia_agent.runtime.run_context import WenjiaRunContext

PROFILE_RELATIONSHIPS = {"本人", "父亲", "母亲", "伴侣", "子女", "朋友", "其他"}

_adapter = BaziAdapter()

REQUIRED_BIRTH_FIELDS = {
    "name": "姓名或展示名",
    "gender": "性别",
    "birth_year": "出生年",
    "birth_month": "出生月",
    "birth_day": "出生日",
    "birth_hour": "出生小时",
    "birth_minute": "出生分钟",
    "calendar_type": "历法类型（solar 公历 / lunar 农历）",
}


def calculate_bazi(
    name: str,
    gender: str,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_minute: int = 0,
    calendar_type: str = "solar",
    is_leap_month: bool = False,
    province: str | None = None,
    city: str | None = None,
    longitude: float | None = None,
) -> dict:
    """Calculate BaZi data through the deterministic core."""

    try:
        result = _adapter.calculate(
            BirthInfo(
                name=name,
                gender=gender,
                birth_year=birth_year,
                birth_month=birth_month,
                birth_day=birth_day,
                birth_hour=birth_hour,
                birth_minute=birth_minute,
                calendar_type=calendar_type,  # type: ignore[arg-type]
                is_leap_month=is_leap_month,
                province=province,
                city=city,
                longitude=longitude,
            )
        )
        return ToolResult(
            ok=True,
            tool_name="calculate_bazi",
            data=result.model_dump(),
            warnings=result.warnings,
        ).model_dump()
    except Exception as exc:  # noqa: BLE001 - tool boundary.
        return ToolResult(ok=False, tool_name="calculate_bazi", message=str(exc)).model_dump()


def validate_birth_info(
    name: str | None = None,
    gender: str | None = None,
    birth_year: int | None = None,
    birth_month: int | None = None,
    birth_day: int | None = None,
    birth_hour: int | None = None,
    birth_minute: int | None = None,
    calendar_type: str | None = None,
    is_leap_month: bool | None = None,
    province: str | None = None,
    city: str | None = None,
    longitude: float | None = None,
) -> dict:
    """Validate whether a complete birth profile is available before analysis."""

    values = {
        "name": name,
        "gender": gender,
        "birth_year": birth_year,
        "birth_month": birth_month,
        "birth_day": birth_day,
        "birth_hour": birth_hour,
        "birth_minute": birth_minute,
        "calendar_type": calendar_type,
    }
    missing_fields = [
        label
        for field_name, label in REQUIRED_BIRTH_FIELDS.items()
        if values[field_name] is None or values[field_name] == ""
    ]

    if calendar_type == "lunar" and is_leap_month is None:
        missing_fields.append("是否闰月")

    has_place = bool(province and city) or longitude is not None
    if not has_place:
        missing_fields.append("出生地（省市）或出生地经度")
    elif bool(province) != bool(city):
        missing_fields.append("完整出生地（省份和城市需要同时提供）")

    complete = not missing_fields
    next_question = None
    if not complete:
        next_question = "请先补充完整出生信息：" + "、".join(missing_fields) + "。"

    return ToolResult(
        ok=complete,
        tool_name="validate_birth_info",
        data={
            "complete": complete,
            "missing_fields": missing_fields,
            "next_question": next_question,
        },
        message=None if complete else next_question,
    ).model_dump()


def list_provinces() -> dict:
    """List supported Chinese provinces/regions."""
    return ToolResult(
        ok=True,
        tool_name="list_provinces",
        data={"provinces": get_provinces()},
    ).model_dump()


def list_cities(province: str) -> dict:
    """List supported cities for a province."""
    cities = get_cities(province)
    return ToolResult(
        ok=bool(cities),
        tool_name="list_cities",
        data={"cities": cities},
        message=None if cities else "未找到该省份的城市列表。",
    ).model_dump()


def build_bazi_context_data(
    name: str,
    gender: str,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_minute: int = 0,
    calendar_type: str = "solar",
    is_leap_month: bool = False,
    province: str | None = None,
    city: str | None = None,
    longitude: float | None = None,
) -> dict:
    """Build deterministic Agent context from birth data."""

    bazi_result = calculate_bazi(
        name=name,
        gender=gender,
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_minute=birth_minute,
        calendar_type=calendar_type,
        is_leap_month=is_leap_month,
        province=province,
        city=city,
        longitude=longitude,
    )
    if not bazi_result["ok"]:
        return ToolResult(
            ok=False,
            tool_name="build_bazi_context",
            message=bazi_result.get("message"),
            warnings=bazi_result.get("warnings", []),
        ).model_dump()

    data = bazi_result.get("data") or {}
    context = build_bazi_context(BaziResult.model_validate(data))
    return ToolResult(
        ok=True,
        tool_name="build_bazi_context",
        data={
            "bazi": data,
            "context": context.model_dump(),
        },
        warnings=context.warnings,
    ).model_dump()


def build_luck_cycle_context_data(
    name: str,
    gender: str,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_minute: int = 0,
    calendar_type: str = "solar",
    is_leap_month: bool = False,
    province: str | None = None,
    city: str | None = None,
    longitude: float | None = None,
    target_year: int | None = None,
) -> dict:
    """Build deterministic DaYun/LiuNian context from birth data."""

    try:
        birth_info = BirthInfo(
            name=name,
            gender=gender,
            birth_year=birth_year,
            birth_month=birth_month,
            birth_day=birth_day,
            birth_hour=birth_hour,
            birth_minute=birth_minute,
            calendar_type=calendar_type,  # type: ignore[arg-type]
            is_leap_month=is_leap_month,
            province=province,
            city=city,
            longitude=longitude,
        )
        bazi_result = _adapter.calculate(birth_info)
        luck_cycle = _adapter.calculator.calculate_luck_cycles(
            year=bazi_result.actual_birth_year,
            month=bazi_result.actual_birth_month,
            day=bazi_result.actual_birth_day,
            hour=birth_info.birth_hour,
            minute=birth_info.birth_minute,
            gender=birth_info.gender,
            target_year=target_year,
            use_solar_time=True,
            longitude=bazi_result.longitude,
        )
        return ToolResult(
            ok=True,
            tool_name="build_luck_cycle_context",
            data={
                "bazi": bazi_result.model_dump(),
                "luck_cycle": luck_cycle,
            },
            warnings=bazi_result.warnings,
        ).model_dump()
    except Exception as exc:  # noqa: BLE001 - tool boundary.
        return ToolResult(
            ok=False,
            tool_name="build_luck_cycle_context",
            message=str(exc),
        ).model_dump()


@function_tool
def validate_birth_info_tool(
    name: str | None = None,
    gender: str | None = None,
    birth_year: int | None = None,
    birth_month: int | None = None,
    birth_day: int | None = None,
    birth_hour: int | None = None,
    birth_minute: int | None = None,
    calendar_type: str | None = None,
    is_leap_month: bool | None = None,
    province: str | None = None,
    city: str | None = None,
    longitude: float | None = None,
) -> dict:
    """Check required birth profile fields before charting, analysis, or naming."""

    return validate_birth_info(
        name=name,
        gender=gender,
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_minute=birth_minute,
        calendar_type=calendar_type,
        is_leap_month=is_leap_month,
        province=province,
        city=city,
        longitude=longitude,
    )


def _dedup_charting(
    ctx: RunContextWrapper[WenjiaRunContext] | None,
    tool_name: str,
    arguments: dict,
    compute,
) -> dict:
    """Memoize a deterministic charting tool per run to prevent identical re-calls."""

    run_context = getattr(ctx, "context", None)
    if not isinstance(run_context, WenjiaRunContext):
        return compute(**arguments)

    key = run_context.cache_key(tool_name, arguments)
    cached = run_context.cached_result(key)
    if cached is not None:
        return cached
    return run_context.store_result(key, compute(**arguments))


@function_tool
def calculate_bazi_tool(
    ctx: RunContextWrapper[WenjiaRunContext],
    name: str,
    gender: str,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_minute: int = 0,
    calendar_type: str = "solar",
    is_leap_month: bool = False,
    province: str | None = None,
    city: str | None = None,
    longitude: float | None = None,
) -> dict:
    """Calculate BaZi pillars and extended deterministic metaphysics fields.

    Use this tool whenever BaZi, five elements, ten gods, NaYin, ShenSha, or
    true solar time are needed. Never infer these values directly in the model.
    """

    return _dedup_charting(
        ctx,
        "calculate_bazi_tool",
        dict(
            name=name,
            gender=gender,
            birth_year=birth_year,
            birth_month=birth_month,
            birth_day=birth_day,
            birth_hour=birth_hour,
            birth_minute=birth_minute,
            calendar_type=calendar_type,
            is_leap_month=is_leap_month,
            province=province,
            city=city,
            longitude=longitude,
        ),
        calculate_bazi,
    )


@function_tool
def build_bazi_context_tool(
    ctx: RunContextWrapper[WenjiaRunContext],
    name: str,
    gender: str,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_minute: int = 0,
    calendar_type: str = "solar",
    is_leap_month: bool = False,
    province: str | None = None,
    city: str | None = None,
    longitude: float | None = None,
) -> dict:
    """Build a deterministic BaZi context package for report-style Agents."""

    result = _dedup_charting(
        ctx,
        "build_bazi_context_tool",
        dict(
            name=name,
            gender=gender,
            birth_year=birth_year,
            birth_month=birth_month,
            birth_day=birth_day,
            birth_hour=birth_hour,
            birth_minute=birth_minute,
            calendar_type=calendar_type,
            is_leap_month=is_leap_month,
            province=province,
            city=city,
            longitude=longitude,
        ),
        build_bazi_context_data,
    )
    return result


@function_tool
def build_luck_cycle_context_tool(
    ctx: RunContextWrapper[WenjiaRunContext],
    name: str,
    gender: str,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_minute: int = 0,
    calendar_type: str = "solar",
    is_leap_month: bool = False,
    province: str | None = None,
    city: str | None = None,
    longitude: float | None = None,
    target_year: int | None = None,
) -> dict:
    """Build deterministic DaYun/LiuNian context for fortune analysis.

    Use when users ask about 大运、流年、未来年份、某年运势、十年运势、
    大运切换期, or timing questions. Never infer DaYun/LiuNian directly.
    """

    return _dedup_charting(
        ctx,
        "build_luck_cycle_context_tool",
        dict(
            name=name,
            gender=gender,
            birth_year=birth_year,
            birth_month=birth_month,
            birth_day=birth_day,
            birth_hour=birth_hour,
            birth_minute=birth_minute,
            calendar_type=calendar_type,
            is_leap_month=is_leap_month,
            province=province,
            city=city,
            longitude=longitude,
            target_year=target_year,
        ),
        build_luck_cycle_context_data,
    )


def _run_context(ctx: RunContextWrapper[WenjiaRunContext] | None) -> WenjiaRunContext | None:
    run_context = getattr(ctx, "context", None)
    return run_context if isinstance(run_context, WenjiaRunContext) else None


def _save_profile(
    run_context: WenjiaRunContext | None,
    relationship_type: str,
    arguments: dict,
    custom_relationship: str | None = None,
) -> dict:
    """Chart a person and persist them as a conversation profile.

    Extracted from the tool wrapper so the ctx→session→persist path is unit
    testable without constructing SDK tool-call plumbing.
    """

    relationship = relationship_type.strip()
    if relationship not in PROFILE_RELATIONSHIPS:
        return ToolResult(
            ok=False,
            tool_name="save_profile_tool",
            message="与本人关系必须先确认，并映射为固定关系枚举。",
        ).model_dump()
    custom = (custom_relationship or "").strip()
    if relationship == "其他" and not custom:
        return ToolResult(
            ok=False,
            tool_name="save_profile_tool",
            message="关系为“其他”时，必须先确认并提供关系说明。",
        ).model_dump()

    built = build_bazi_context_data(**arguments)
    if not built["ok"]:
        return built

    data = built.get("data") or {}
    bazi = data.get("bazi") or {}
    context = data.get("context") or {}
    if custom:
        context = {**context, "custom_relationship": custom}

    profile_writer = getattr(run_context, "profile_writer", None) if run_context else None
    if profile_writer is None:
        return ToolResult(
            ok=False,
            tool_name="save_profile_tool",
            data={"saved": False, "relationship_type": relationship, "context": context},
            message="必须登录后才能保存人物档案。",
            warnings=built.get("warnings", []),
        ).model_dump()

    try:
        saved = profile_writer(relationship, bazi, context)
    except Exception as exc:  # noqa: BLE001 - surface persistence failures to the Agent.
        message = str(exc).strip() or "保存人物档案时发生未知错误。"
        return ToolResult(
            ok=False,
            tool_name="save_profile_tool",
            data={"saved": False, "relationship_type": relationship, "context": context},
            message=f"档案保存失败：{message}",
            warnings=built.get("warnings", []),
        ).model_dump()
    return ToolResult(
        ok=True,
        tool_name="save_profile_tool",
        data={"saved": True, "profile": saved, "context": context},
        warnings=built.get("warnings", []),
    ).model_dump()


@function_tool
def save_profile_tool(
    ctx: RunContextWrapper[WenjiaRunContext],
    name: str,
    gender: str,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_minute: int = 0,
    calendar_type: str = "solar",
    is_leap_month: bool = False,
    province: str | None = None,
    city: str | None = None,
    longitude: float | None = None,
    relationship_type: str = "本人",
    custom_relationship: str | None = None,
) -> dict:
    """Chart a person and save them as a conversation profile (人物档案).

    Use after a complete birth profile is confirmed to persist 本人 / 父亲 / 母亲
    etc., so later turns and the naming Agent can reuse their BaZi. Re-saving the
    same person updates the existing record instead of duplicating it.
    """

    return _save_profile(
        _run_context(ctx),
        relationship_type,
        dict(
            name=name,
            gender=gender,
            birth_year=birth_year,
            birth_month=birth_month,
            birth_day=birth_day,
            birth_hour=birth_hour,
            birth_minute=birth_minute,
            calendar_type=calendar_type,
            is_leap_month=is_leap_month,
            province=province,
            city=city,
            longitude=longitude,
        ),
        custom_relationship,
    )


def _list_profiles(run_context: WenjiaRunContext | None) -> dict:
    explicit_profiles = getattr(run_context, "profile_context", None) if run_context else None
    if explicit_profiles:
        return ToolResult(
            ok=True,
            tool_name="list_profiles_tool",
            data={"profiles": explicit_profiles},
        ).model_dump()
    return ToolResult(
        ok=True,
        tool_name="list_profiles_tool",
        data={"profiles": explicit_profiles or []},
    ).model_dump()


def _list_long_term_memories(run_context: WenjiaRunContext | None) -> dict:
    user_id = getattr(run_context, "user_id", None) if run_context else None
    if not user_id:
        return ToolResult(
            ok=True,
            tool_name="list_long_term_memories_tool",
            data={"memories": []},
            message="未提供长期记忆标识，无法读取跨会话记忆。",
        ).model_dump()

    return ToolResult(
        ok=True,
        tool_name="list_long_term_memories_tool",
        data={"memories": memory_store.list_memories(user_id)},
    ).model_dump()


@function_tool
def list_profiles_tool(ctx: RunContextWrapper[WenjiaRunContext]) -> dict:
    """List person profiles already saved in the current conversation.

    Use to reuse existing 本人/父母 profiles instead of re-asking for their
    birth info, for example before generating naming suggestions.
    """

    return _list_profiles(_run_context(ctx))


@function_tool
def list_long_term_memories_tool(ctx: RunContextWrapper[WenjiaRunContext]) -> dict:
    """List compact memories saved across conversations for this caller-owned user id."""

    return _list_long_term_memories(_run_context(ctx))


@function_tool
def list_provinces_tool() -> dict:
    """List supported Chinese provinces/regions for birth place selection."""

    return list_provinces()


@function_tool
def list_cities_tool(province: str) -> dict:
    """List supported cities for a province."""

    return list_cities(province)


BAZI_TOOLS = [
    validate_birth_info_tool,
    calculate_bazi_tool,
    build_bazi_context_tool,
    build_luck_cycle_context_tool,
    list_profiles_tool,
    list_long_term_memories_tool,
    list_provinces_tool,
    list_cities_tool,
]

# ProfileAgent collects birth info and charts once. It deliberately omits
# ``calculate_bazi_tool`` so the model has a single charting path
# (``build_bazi_context_tool`` already includes the four-pillar calculation),
# which removes the back-and-forth that caused the max-turns loop. It saves the
# charted person as a 本人 profile via ``save_profile_tool``.
PROFILE_TOOLS = [
    validate_birth_info_tool,
    build_bazi_context_tool,
    build_luck_cycle_context_tool,
    save_profile_tool,
    list_profiles_tool,
    list_long_term_memories_tool,
    list_provinces_tool,
    list_cities_tool,
]

# NamingAgent charts the subject plus optional parents (saved as 父亲/母亲
# profiles) and reuses any already-stored profiles in the conversation.
NAMING_TOOLS = [
    validate_birth_info_tool,
    build_bazi_context_tool,
    build_luck_cycle_context_tool,
    save_profile_tool,
    list_profiles_tool,
    list_long_term_memories_tool,
    list_provinces_tool,
    list_cities_tool,
]
