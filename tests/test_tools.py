from wenjia_agent.tools.bazi_tools import (
    build_bazi_context_data,
    build_luck_cycle_context_data,
    calculate_bazi,
    list_cities,
    list_provinces,
    validate_birth_info,
)


def test_calculate_bazi_tool_data_shape():
    result = calculate_bazi(
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

    assert result["ok"] is True
    assert result["tool_name"] == "calculate_bazi"
    assert result["data"]["year_pillar"]
    assert result["data"]["five_elements"]["火"] >= 0


def test_build_bazi_context_tool_data_shape():
    result = build_bazi_context_data(
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

    assert result["ok"] is True
    assert result["tool_name"] == "build_bazi_context"
    assert result["data"]["context"]["pillars"]["day"]
    assert set(result["data"]["context"]["five_element_balance"]["counts"]) == {
        "木",
        "火",
        "土",
        "金",
        "水",
    }


def test_build_luck_cycle_context_tool_data_shape():
    result = build_luck_cycle_context_data(
        name="测试",
        gender="男",
        birth_year=1990,
        birth_month=5,
        birth_day=10,
        birth_hour=15,
        birth_minute=0,
        province="北京市",
        city="北京市",
        target_year=2026,
    )

    assert result["ok"] is True
    assert result["tool_name"] == "build_luck_cycle_context"
    luck = result["data"]["luck_cycle"]
    assert luck["direction"] in {"顺行", "逆行"}
    assert luck["start"]["solar_date"]
    assert luck["target_year"] == 2026
    assert luck["target_da_yun"]["is_target"] is True
    assert luck["target_liu_nian"]["year"] == 2026
    assert len(luck["target_cycle_annual_years"]) >= 1


def test_build_luck_cycle_context_requires_binary_gender():
    result = build_luck_cycle_context_data(
        name="测试",
        gender="未知",
        birth_year=1990,
        birth_month=5,
        birth_day=10,
        birth_hour=15,
        birth_minute=0,
        province="北京市",
        city="北京市",
        target_year=2026,
    )

    assert result["ok"] is False
    assert "性别" in result["message"]


def test_city_tools_data_shape():
    provinces = list_provinces()
    cities = list_cities("北京市")

    assert provinces["ok"] is True
    assert "北京市" in provinces["data"]["provinces"]
    assert cities["ok"] is True
    assert "北京市" in cities["data"]["cities"]


def test_validate_birth_info_requires_complete_birth_profile():
    result = validate_birth_info(
        name="测试",
        birth_year=1995,
        birth_month=5,
        birth_day=12,
    )

    assert result["ok"] is False
    assert result["tool_name"] == "validate_birth_info"
    assert "性别" in result["data"]["missing_fields"]
    assert "出生小时" in result["data"]["missing_fields"]
    assert "出生地（省市）或出生地经度" in result["data"]["missing_fields"]


def test_validate_birth_info_accepts_complete_birth_profile():
    result = validate_birth_info(
        name="测试",
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

    assert result["ok"] is True
    assert result["data"]["complete"] is True
    assert result["data"]["missing_fields"] == []
