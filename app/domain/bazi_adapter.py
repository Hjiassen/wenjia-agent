"""Adapter between OpenAI Agent tools and the deterministic BaZi core."""

from __future__ import annotations

from dataclasses import dataclass

from lunar_python import Lunar

from app.core.bazi_calculator import BaziCalculator
from app.core.city_data import get_cities, get_city_coordinates
from app.domain.schemas import BaziResult, BirthInfo


@dataclass(frozen=True)
class _ActualDate:
    year: int
    month: int
    day: int


class BaziAdapter:
    """Thin adapter around the current project's BaZi logic.

    The Agent layer must not ask the model to calculate pillars. All deterministic
    calculation goes through this adapter and the copied core modules.
    """

    def __init__(self) -> None:
        self.calculator = BaziCalculator()

    def calculate(self, birth_info: BirthInfo) -> BaziResult:
        warnings: list[str] = []
        actual_date = self._normalize_calendar(birth_info)
        longitude, longitude_warnings = self._resolve_longitude(birth_info)
        warnings.extend(longitude_warnings)

        bazi_data = self.calculator.calculate_bazi(
            actual_date.year,
            actual_date.month,
            actual_date.day,
            birth_info.birth_hour,
            birth_info.birth_minute,
            use_solar_time=True,
            longitude=longitude,
        )

        five_elements = self.calculator.get_five_elements_analysis(
            bazi_data,
            year=bazi_data.get("solar_year", actual_date.year),
            month=bazi_data.get("solar_month", actual_date.month),
            day=bazi_data.get("solar_day", actual_date.day),
            hour=bazi_data.get("solar_hour", birth_info.birth_hour),
            minute=bazi_data.get("solar_minute", birth_info.birth_minute),
        )

        return BaziResult(
            name=birth_info.name,
            gender=birth_info.gender,
            input_calendar_type=birth_info.calendar_type,
            actual_birth_year=actual_date.year,
            actual_birth_month=actual_date.month,
            actual_birth_day=actual_date.day,
            longitude=longitude,
            warnings=warnings,
            five_elements=five_elements,
            **bazi_data,
        )

    def _normalize_calendar(self, birth_info: BirthInfo) -> _ActualDate:
        if birth_info.calendar_type == "solar":
            return _ActualDate(
                birth_info.birth_year,
                birth_info.birth_month,
                birth_info.birth_day,
            )

        try:
            lunar_month = -birth_info.birth_month if birth_info.is_leap_month else birth_info.birth_month
            lunar = Lunar.fromYmd(birth_info.birth_year, lunar_month, birth_info.birth_day)
            solar = lunar.getSolar()
        except Exception as exc:  # noqa: BLE001 - normalize library errors for tool callers.
            raise ValueError(
                "无效的农历日期："
                f"{birth_info.birth_year}年"
                f"{'闰' if birth_info.is_leap_month else ''}"
                f"{birth_info.birth_month}月{birth_info.birth_day}日"
            ) from exc

        return _ActualDate(solar.getYear(), solar.getMonth(), solar.getDay())

    def _resolve_longitude(self, birth_info: BirthInfo) -> tuple[float, list[str]]:
        warnings: list[str] = []

        if birth_info.province and birth_info.city:
            cities = get_cities(birth_info.province)
            if birth_info.city not in cities:
                warnings.append("未找到精确城市经纬度，已默认使用北京经度。")
            longitude, _latitude = get_city_coordinates(birth_info.province, birth_info.city)
            return float(longitude), warnings

        if birth_info.longitude is not None:
            return float(birth_info.longitude), warnings

        warnings.append("未提供出生地或经度，已默认使用北京经度。")
        return 116.4074, warnings
