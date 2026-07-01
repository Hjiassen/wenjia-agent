from wenjia_agent.domain.bazi_adapter import BaziAdapter
from wenjia_agent.domain.schemas import BirthInfo


def test_calculate_bazi_solar_beijing():
    result = BaziAdapter().calculate(
        BirthInfo(
            name="测试",
            gender="未知",
            birth_year=1995,
            birth_month=5,
            birth_day=12,
            birth_hour=9,
            birth_minute=30,
            province="北京市",
            city="北京市",
        )
    )

    assert result.year_pillar
    assert result.month_pillar
    assert result.day_pillar
    assert result.hour_pillar
    assert set(result.five_elements) == {"木", "火", "土", "金", "水"}


def test_calculate_bazi_lunar():
    result = BaziAdapter().calculate(
        BirthInfo(
            name="农历测试",
            gender="未知",
            birth_year=1995,
            birth_month=4,
            birth_day=13,
            birth_hour=9,
            birth_minute=30,
            calendar_type="lunar",
            longitude=116.4074,
        )
    )

    assert result.input_calendar_type == "lunar"
    assert result.actual_birth_year >= 1995
    assert result.year_pillar
