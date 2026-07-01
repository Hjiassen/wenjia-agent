from wenjia_agent.domain.schemas import (
    AnalysisSection,
    FortuneReport,
    NamingReport,
    NamingSuggestion,
    RelationshipReport,
)
from wenjia_agent.runtime.output_format import format_final_output


def test_plain_string_passes_through():
    assert format_final_output("你好") == "你好"


def test_fortune_report_renders_markdown():
    report = FortuneReport(
        report_title="事业命理分析报告",
        profile_name="测试",
        bazi_summary=["八字：乙亥 辛巳 癸卯 丁巳"],
        sections=[
            AnalysisSection(
                title="命格与事业基调",
                summary="身弱财旺，先积累核心竞争力。",
                deterministic_basis=["日主癸水，身弱"],
                suggestions=["深耕技术专业路线"],
            )
        ],
        action_items=["优先深耕专业技能"],
    )
    md = format_final_output(report)

    assert md.startswith("# 事业命理分析报告")
    assert "### 命格与事业基调" in md
    assert "- 日主癸水，身弱" in md
    assert "## 行动建议" in md
    # No raw pydantic repr leaking through.
    assert "report_title=" not in md
    assert "AnalysisSection(" not in md


def test_naming_report_renders_suggestions():
    report = NamingReport(
        report_title="起名建议",
        profile_name="宝宝",
        element_strategy=["补水增金"],
        parent_references=["父亲 甲子 乙丑 丙寅 丁卯"],
        suggestions=[
            NamingSuggestion(
                name="李沐",
                pinyin="Lǐ Mù",
                element_focus=["水"],
                reasoning=["沐字含水"],
                caveats=["注意重名"],
            )
        ],
        screening_checklist=["读音顺口"],
    )
    md = format_final_output(report)

    assert "## 父母八字参考" in md
    assert "### 李沐（Lǐ Mù）" in md
    assert "## 筛选清单" in md


def test_relationship_report_renders_markdown():
    report = RelationshipReport(
        report_title="合盘报告",
        subject_names=["甲", "乙"],
        shared_basis=["双方日主相生"],
        sections=[AnalysisSection(title="相处模式", summary="互补。")],
        communication_suggestions=["多倾听"],
    )
    md = format_final_output(report)

    assert md.startswith("# 合盘报告")
    assert "甲、乙" in md
    assert "## 沟通建议" in md
