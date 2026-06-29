"""OpenAI Agents SDK tools for deterministic BaZi calculation."""

from __future__ import annotations

from agents import function_tool

from app.core.city_data import get_cities, get_provinces
from app.domain.context_builders import build_bazi_context
from app.domain.bazi_adapter import BaziAdapter
from app.domain.schemas import BaziResult, BirthInfo, ToolResult

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


@function_tool
def calculate_bazi_tool(
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

    return calculate_bazi(
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


@function_tool
def build_bazi_context_tool(
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

    return build_bazi_context_data(
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
    list_provinces_tool,
    list_cities_tool,
]
