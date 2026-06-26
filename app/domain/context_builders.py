"""Deterministic context builders for Agent prompts and tools."""

from __future__ import annotations

from app.domain.schemas import BaziContext, BaziResult, ElementBalance

ELEMENT_ORDER = ("木", "火", "土", "金", "水")


def analyze_element_balance(counts: dict[str, int]) -> ElementBalance:
    """Build a simple deterministic five-element balance summary."""

    normalized = {element: int(counts.get(element, 0)) for element in ELEMENT_ORDER}
    total = sum(normalized.values())
    average = total / len(ELEMENT_ORDER) if ELEMENT_ORDER else 0.0
    if not normalized:
        return ElementBalance(
            counts={},
            dominant_elements=[],
            weak_elements=[],
            missing_elements=[],
            total_count=0,
            average_count=0.0,
        )

    max_count = max(normalized.values())
    min_count = min(normalized.values())
    dominant = [element for element, count in normalized.items() if count == max_count and count > 0]
    missing = [element for element, count in normalized.items() if count == 0]
    weak = [
        element
        for element, count in normalized.items()
        if count == min_count and count > 0 and count < average
    ]

    return ElementBalance(
        counts=normalized,
        dominant_elements=dominant,
        weak_elements=weak,
        missing_elements=missing,
        total_count=total,
        average_count=round(average, 2),
    )


def build_bazi_context(result: BaziResult) -> BaziContext:
    """Convert a raw BaZi result into Agent-facing deterministic context."""

    actual_date = (
        f"{result.actual_birth_year:04d}-"
        f"{result.actual_birth_month:02d}-"
        f"{result.actual_birth_day:02d}"
    )
    true_solar_time = None
    if result.solar_year and result.solar_month and result.solar_day and result.solar_hour is not None:
        minute = result.solar_minute if result.solar_minute is not None else 0
        true_solar_time = (
            f"{result.solar_year:04d}-{result.solar_month:02d}-{result.solar_day:02d} "
            f"{result.solar_hour:02d}:{minute:02d}"
        )

    return BaziContext(
        profile_name=result.name,
        gender=result.gender,
        calendar_type=result.input_calendar_type,
        actual_solar_date=actual_date,
        true_solar_time=true_solar_time,
        longitude=result.longitude,
        pillars={
            "year": result.year_pillar,
            "month": result.month_pillar,
            "day": result.day_pillar,
            "hour": result.hour_pillar,
        },
        five_element_balance=analyze_element_balance(result.five_elements),
        ten_gods=result.ten_gods,
        nayin=result.nayin,
        shen_sha=result.shen_sha,
        kong_wang=result.kong_wang,
        life_palaces={
            "tai_yuan": result.tai_yuan,
            "tai_yuan_nayin": result.tai_yuan_nayin,
            "ming_gong": result.ming_gong,
            "ming_gong_nayin": result.ming_gong_nayin,
            "shen_gong": result.shen_gong,
            "shen_gong_nayin": result.shen_gong_nayin,
            "tai_xi": result.tai_xi,
            "tai_xi_nayin": result.tai_xi_nayin,
        },
        warnings=result.warnings,
    )
