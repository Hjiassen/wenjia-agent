from wenjia_agent.domain.schemas import (
    AnalysisSection,
    FortuneReport,
    NamingReport,
    NamingSuggestion,
    RelationshipReport,
)
from agents.agent_output import AgentOutputSchema


def test_report_schemas_are_instantiable():
    section = AnalysisSection(
        title="总览",
        summary="基于工具结果的摘要。",
        deterministic_basis=["日主与五行分布"],
        suggestions=["保持现实验证"],
    )

    fortune = FortuneReport(
        report_title="命格分析",
        profile_name="测试",
        sections=[section],
    )
    relationship = RelationshipReport(
        report_title="关系分析",
        subject_names=["甲", "乙"],
        sections=[section],
    )
    naming = NamingReport(
        report_title="起名建议",
        profile_name="测试",
        suggestions=[
            NamingSuggestion(
                name="问甲",
                element_focus=["木"],
                reasoning=["读音清楚", "寓意直接"],
            )
        ],
    )

    assert fortune.boundary_note
    assert relationship.communication_suggestions == []
    assert naming.suggestions[0].name == "问甲"


def test_report_schemas_are_compatible_with_agents_sdk():
    for schema_type in (FortuneReport, RelationshipReport, NamingReport):
        schema = AgentOutputSchema(schema_type).json_schema()

        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
