"""Deterministic output guardrails for Agent replies.

These checks power the harness Verify stage. They are pure functions (no LLM, no
network) so they are cheap, fully testable, and safe to run on every reply:

- structured reports must keep a non-empty boundary note;
- replies must not make absolute/fear-mongering claims;
- a fortune report's stated 八字 must match the deterministic chart on file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.domain.schemas import FortuneReport, NamingReport, RelationshipReport

# Phrases that turn a "for reference only" reading into a deterministic promise or
# a scare. Kept conservative to avoid false positives on benign text.
ABSOLUTE_CLAIM_PATTERNS = [
    "一定会",
    "必然会",
    "必定",
    "肯定会",
    "百分之百",
    "100%",
    "保证你",
    "注定",
    "在劫难逃",
    "血光之灾",
    "必有大难",
    "必死",
    "稳赚不赔",
    "包你",
]

_PILLAR = "[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]"


@dataclass(frozen=True)
class Issue:
    """A single guardrail / verification finding."""

    code: str
    message: str
    severity: str = "error"  # "error" triggers a revision; "warn" is remediated/logged.


def check_non_empty(rendered_text: str) -> list[Issue]:
    if not rendered_text or not rendered_text.strip():
        return [Issue("empty_output", "回复为空。", "error")]
    return []


def check_boundary_note(structured: Any) -> list[Issue]:
    """Structured reports must carry a non-empty boundary note."""

    if isinstance(structured, (FortuneReport, RelationshipReport, NamingReport)):
        if not (structured.boundary_note or "").strip():
            return [Issue("missing_boundary", "结构化报告缺少边界提醒。", "warn")]
    return []


def find_absolute_claims(rendered_text: str) -> list[str]:
    return [phrase for phrase in ABSOLUTE_CLAIM_PATTERNS if phrase in rendered_text]


def check_no_absolute_claims(rendered_text: str) -> list[Issue]:
    hits = find_absolute_claims(rendered_text)
    if hits:
        return [
            Issue(
                "absolute_claim",
                "包含绝对化或恐吓性措辞：" + "、".join(hits),
                "error",
            )
        ]
    return []


def _ground_truth_pillars(report: FortuneReport, profiles: list[dict]) -> list[str] | None:
    """Resolve the deterministic four pillars for the report's subject."""

    if not profiles:
        return None
    match = next((p for p in profiles if p.get("name") == report.profile_name), None)
    if match is None:
        match = next((p for p in profiles if p.get("relationship_type") == "本人"), None)
    if match is None and len(profiles) == 1:
        match = profiles[0]
    if match is None:
        return None
    pillars = match.get("pillars") or {}
    ordered = [pillars.get("year"), pillars.get("month"), pillars.get("day"), pillars.get("hour")]
    cleaned = [p for p in ordered if p]
    return cleaned if len(cleaned) == 4 else None


def check_bazi_consistency(structured: Any, profiles: list[dict]) -> list[Issue]:
    """A fortune report's explicit 八字 line must match the chart on file."""

    if not isinstance(structured, FortuneReport):
        return []
    ground = _ground_truth_pillars(structured, profiles)
    if ground is None:
        return []
    for line in structured.bazi_summary:
        if "八字" not in line:
            continue
        claimed = re.findall(_PILLAR, line)
        if len(claimed) == 4 and claimed != ground:
            return [
                Issue(
                    "bazi_mismatch",
                    f"报告四柱 {' '.join(claimed)} 与排盘结果 {' '.join(ground)} 不一致。",
                    "error",
                )
            ]
    return []


def run_output_checks(
    rendered_text: str,
    structured: Any,
    profiles: list[dict] | None = None,
) -> list[Issue]:
    """Run all output guardrails and return the combined findings."""

    issues = check_non_empty(rendered_text)
    if issues:
        return issues  # nothing else is meaningful on empty output.
    issues.extend(check_boundary_note(structured))
    issues.extend(check_no_absolute_claims(rendered_text))
    issues.extend(check_bazi_consistency(structured, profiles or []))
    return issues
