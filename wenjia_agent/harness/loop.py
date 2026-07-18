"""The harness control loop: Act → Verify → Revise → Finalize."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from wenjia_agent.guardrails.output_checks import Issue
from wenjia_agent.harness.policy import HarnessPolicy

DEFAULT_BOUNDARY = "命理内容仅作文化娱乐与个人参考。"

# act(correction) runs the agent once; correction is None on the first attempt,
# or a feedback instruction on a revision.
ActFn = Callable[[str | None], Awaitable["ActOutcome"]]
VerifyFn = Callable[["ActOutcome"], list[Issue]]
EventFn = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass
class ActOutcome:
    """Result of one agent run."""

    final_output: Any
    rendered_text: str


@dataclass
class HarnessResult:
    """Final harness outcome after verification and any revisions."""

    rendered_text: str
    issues: list[Issue] = field(default_factory=list)
    attempts: int = 0  # number of revision attempts performed (0 = first try passed)


def _errors(issues: list[Issue]) -> list[Issue]:
    return [issue for issue in issues if issue.severity == "error"]


def build_correction(errors: list[Issue]) -> str:
    """Turn verification errors into a revision instruction for the model."""

    bullets = "\n".join(f"- {issue.message}" for issue in errors)
    return (
        "你上一条回复存在以下问题，请在保持原有结构与确定性命盘事实的前提下修正后重新输出：\n"
        f"{bullets}\n"
        "要求：不得使用绝对化或恐吓性措辞；命盘四柱必须与排盘工具结果一致；"
        "保留『仅作文化娱乐与个人参考』的边界提醒。"
    )


def _remediate(text: str, issues: list[Issue]) -> str:
    """Deterministic, content-preserving fixes for residual warn-level issues."""

    if any(issue.code == "missing_boundary" for issue in issues):
        if DEFAULT_BOUNDARY not in text:
            text = f"{text}\n\n> {DEFAULT_BOUNDARY}"
    return text


async def run_harness(
    act: ActFn,
    verify: VerifyFn,
    policy: HarnessPolicy,
    on_event: EventFn | None = None,
) -> HarnessResult:
    """Drive one harnessed run: act, verify, revise up to the policy limit."""

    async def emit(event: dict[str, Any]) -> None:
        if on_event is not None:
            await on_event(event)

    outcome = await act(None)
    issues = verify(outcome)
    attempts = 0

    while policy.revise_enabled and attempts < policy.max_revisions and _errors(issues):
        attempts += 1
        await emit(
            {
                "type": "revise",
                "attempt": attempts,
                "message": f"检测到 {len(_errors(issues))} 处问题，正在第 {attempts} 次修订。",
            }
        )
        outcome = await act(build_correction(_errors(issues)))
        issues = verify(outcome)

    passed = not _errors(issues)
    await emit(
        {
            "type": "verify",
            "success": passed,
            "attempts": attempts,
            "message": "校验通过。" if passed else "校验完成。",
        }
    )

    return HarnessResult(
        rendered_text=_remediate(outcome.rendered_text, issues),
        issues=issues,
        attempts=attempts,
    )
