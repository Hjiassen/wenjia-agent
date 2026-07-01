from wenjia_agent.domain.context_builders import analyze_element_balance, build_bazi_context
from wenjia_agent.domain.bazi_adapter import BaziAdapter
from wenjia_agent.domain.schemas import BirthInfo


def test_analyze_element_balance_identifies_dominant_and_missing():
    balance = analyze_element_balance({"木": 2, "火": 0, "土": 1, "金": 4, "水": 1})

    assert balance.dominant_elements == ["金"]
    assert balance.missing_elements == ["火"]
    assert balance.total_count == 8


def test_build_bazi_context_from_result():
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

    context = build_bazi_context(result)

    assert context.profile_name == "测试"
    assert context.pillars["year"] == result.year_pillar
    assert context.five_element_balance.total_count > 0
