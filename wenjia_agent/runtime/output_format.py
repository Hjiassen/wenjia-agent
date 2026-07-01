"""Render Agent final outputs into Markdown for display.

Specialist Agents (fortune / relationship / naming) use structured
``output_type`` models, so ``result.final_output`` is a Pydantic object. Calling
``str()`` on it leaks the raw ``field=value`` repr to the UI. This module turns
those reports into readable Markdown; plain-text outputs pass through unchanged.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from wenjia_agent.domain.schemas import (
    AnalysisSection,
    FortuneReport,
    NamingReport,
    RelationshipReport,
)


def _bullets(items: list[str], indent: str = "") -> list[str]:
    return [f"{indent}- {item}" for item in items if item]


def _section_md(section: AnalysisSection) -> list[str]:
    lines = [f"### {section.title}", "", section.summary, ""]
    if section.deterministic_basis:
        lines.append("**命盘依据**")
        lines.extend(_bullets(section.deterministic_basis))
        lines.append("")
    if section.suggestions:
        lines.append("**建议**")
        lines.extend(_bullets(section.suggestions))
        lines.append("")
    return lines


def _fortune_md(report: FortuneReport) -> str:
    lines = [f"# {report.report_title}", "", f"**对象**：{report.profile_name}", ""]
    if report.bazi_summary:
        lines.append("## 命盘摘要")
        lines.extend(_bullets(report.bazi_summary))
        lines.append("")
    for section in report.sections:
        lines.extend(_section_md(section))
    if report.action_items:
        lines.append("## 行动建议")
        lines.extend(_bullets(report.action_items))
        lines.append("")
    lines.append(f"> {report.boundary_note}")
    return "\n".join(lines).strip()


def _relationship_md(report: RelationshipReport) -> str:
    names = "、".join(report.subject_names) if report.subject_names else "—"
    lines = [f"# {report.report_title}", "", f"**对象**：{names}", ""]
    if report.shared_basis:
        lines.append("## 共同命盘依据")
        lines.extend(_bullets(report.shared_basis))
        lines.append("")
    for section in report.sections:
        lines.extend(_section_md(section))
    if report.communication_suggestions:
        lines.append("## 沟通建议")
        lines.extend(_bullets(report.communication_suggestions))
        lines.append("")
    lines.append(f"> {report.boundary_note}")
    return "\n".join(lines).strip()


def _naming_md(report: NamingReport) -> str:
    lines = [f"# {report.report_title}", "", f"**对象**：{report.profile_name}", ""]
    if report.element_strategy:
        lines.append("## 五行起名策略")
        lines.extend(_bullets(report.element_strategy))
        lines.append("")
    if report.parent_references:
        lines.append("## 父母八字参考")
        lines.extend(_bullets(report.parent_references))
        lines.append("")
    if report.suggestions:
        lines.append("## 名字建议")
        lines.append("")
        for suggestion in report.suggestions:
            heading = suggestion.name
            if suggestion.pinyin:
                heading += f"（{suggestion.pinyin}）"
            lines.append(f"### {heading}")
            if suggestion.element_focus:
                lines.append(f"**五行侧重**：{'、'.join(suggestion.element_focus)}")
            if suggestion.reasoning:
                lines.append("")
                lines.append("**解读**")
                lines.extend(_bullets(suggestion.reasoning))
            if suggestion.caveats:
                lines.append("")
                lines.append("**注意**")
                lines.extend(_bullets(suggestion.caveats))
            lines.append("")
    if report.screening_checklist:
        lines.append("## 筛选清单")
        lines.extend(_bullets(report.screening_checklist))
        lines.append("")
    lines.append(f"> {report.boundary_note}")
    return "\n".join(lines).strip()


def format_final_output(output: Any) -> str:
    """Convert an Agent final output into display-ready Markdown text."""

    if isinstance(output, str):
        return output
    if isinstance(output, FortuneReport):
        return _fortune_md(output)
    if isinstance(output, RelationshipReport):
        return _relationship_md(output)
    if isinstance(output, NamingReport):
        return _naming_md(output)
    if isinstance(output, BaseModel):
        # Unknown structured output — fall back to readable JSON rather than repr.
        return output.model_dump_json(indent=2)
    return str(output)
