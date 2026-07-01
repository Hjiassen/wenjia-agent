"""Deterministic BaZi CLI demo that does not require an OpenAI API key."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wenjia_agent.domain.bazi_adapter import BaziAdapter
from wenjia_agent.domain.schemas import BirthInfo


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    _configure_stdout()
    adapter = BaziAdapter()
    result = adapter.calculate(
        BirthInfo(
            name="示例",
            gender="未知",
            birth_year=1995,
            birth_month=5,
            birth_day=12,
            birth_hour=9,
            birth_minute=30,
            calendar_type="solar",
            province="北京市",
            city="北京市",
        )
    )

    print("四柱八字：")
    print(result.year_pillar, result.month_pillar, result.day_pillar, result.hour_pillar)
    print("五行分布：", result.five_elements)
    if result.warnings:
        print("提示：", "；".join(result.warnings))


if __name__ == "__main__":
    main()
