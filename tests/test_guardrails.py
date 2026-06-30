from app.domain.schemas import AnalysisSection, FortuneReport
from app.guardrails.output_checks import (
    check_bazi_consistency,
    check_boundary_note,
    run_output_checks,
)


def _fortune(**overrides) -> FortuneReport:
    base = dict(
        report_title="事业命理分析报告",
        profile_name="测试",
        bazi_summary=["八字：乙亥 辛巳 癸卯 丁巳"],
        sections=[AnalysisSection(title="基调", summary="身弱财旺，先积累实力。")],
        action_items=["深耕专业"],
    )
    base.update(overrides)
    return FortuneReport(**base)


_PROFILES = [
    {
        "id": 1,
        "name": "测试",
        "relationship_type": "本人",
        "gender": "未知",
        "pillars": {"year": "乙亥", "month": "辛巳", "day": "癸卯", "hour": "丁巳"},
        "five_elements": {"木": 3, "火": 6, "土": 1, "金": 3, "水": 3},
    }
]


def test_empty_output_flagged():
    issues = run_output_checks("", "hello")
    assert [i.code for i in issues] == ["empty_output"]


def test_clean_report_has_no_errors():
    issues = run_output_checks("一段稳健、非绝对化的分析。", _fortune(), _PROFILES)
    assert [i for i in issues if i.severity == "error"] == []


def test_absolute_claim_is_error():
    issues = run_output_checks("你今年一定会发大财，必定升职。", _fortune(), _PROFILES)
    codes = {i.code for i in issues if i.severity == "error"}
    assert "absolute_claim" in codes


def test_missing_boundary_is_warn():
    issues = check_boundary_note(_fortune(boundary_note=""))
    assert len(issues) == 1
    assert issues[0].code == "missing_boundary"
    assert issues[0].severity == "warn"


def test_bazi_mismatch_detected():
    bad = _fortune(bazi_summary=["八字：甲子 乙丑 丙寅 丁卯"])
    issues = check_bazi_consistency(bad, _PROFILES)
    assert [i.code for i in issues] == ["bazi_mismatch"]


def test_bazi_match_passes():
    issues = check_bazi_consistency(_fortune(), _PROFILES)
    assert issues == []


def test_bazi_consistency_skipped_without_profile():
    issues = check_bazi_consistency(_fortune(bazi_summary=["八字：甲子 乙丑 丙寅 丁卯"]), [])
    assert issues == []
