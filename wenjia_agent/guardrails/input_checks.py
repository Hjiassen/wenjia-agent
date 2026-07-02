"""Deterministic input guardrails for user requests."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from agents.guardrail import GuardrailFunctionOutput, input_guardrail

from wenjia_agent.runtime.config import settings


@dataclass(frozen=True)
class InputIssue:
    """One input guardrail finding."""

    code: str
    category: str
    message: str
    severity: str = "block"
    matches: tuple[str, ...] = ()


@dataclass(frozen=True)
class InputCheckResult:
    """Combined input guardrail decision."""

    allowed: bool
    issues: tuple[InputIssue, ...] = ()
    response: str | None = None

    @property
    def blocked(self) -> bool:
        return not self.allowed

    def to_trace_payload(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "response": self.response,
            "issues": [asdict(issue) for issue in self.issues],
        }


PROMPT_INJECTION_PATTERNS = [
    r"忽略(之前|以上|所有|原本).*?(指令|规则|要求)",
    r"(泄露|展示|输出|告诉我).*?(系统提示词|隐藏提示词|prompt|system prompt)",
    r"(developer message|system message|system prompt)",
    r"(jailbreak|DAN|越狱)",
    r"(不要|无需).{0,8}(遵守|执行).{0,8}(规则|限制|安全)",
]

HIGH_STAKES_PATTERNS = [
    r"(诊断|确诊).{0,12}(疾病|癌症|抑郁|焦虑|病)",
    r"(怎么|如何).{0,8}(用药|吃药|停药|开药|处方)",
    r"(是否|要不要).{0,8}(手术|住院|停药|离婚|起诉)",
    r"(法律意见|律师函|合同怎么签|起诉状|刑事责任)",
    r"(买哪只|卖哪只|满仓|梭哈|加杠杆|稳赚|保本).{0,12}(股票|基金|币|期货|投资)",
    r"(投资建议|理财建议).{0,12}(买|卖|配置|收益)",
    r"(自杀|轻生|自残|不想活)",
]

UNSAFE_PATTERNS = [
    r"(黑客攻击|盗号|撞库|木马|勒索软件|破解密码)",
    r"(诈骗|洗钱|逃税|绕过风控|伪造证件)",
    r"(制毒|爆炸物|投毒|伤害别人|杀人)",
]

_CATEGORY_RESPONSES = {
    "prompt_injection": (
        "我不能协助绕过系统规则、泄露内部提示或改变安全边界。"
        "你可以继续问排盘、命格、合盘、起名或命理工具相关的问题。"
    ),
    "high_stakes": (
        "这个问题涉及医疗、法律、投资、心理危机或其他高风险决策，我不能给确定性建议。"
        "命理内容只能作为文化娱乐与个人参考；关键决策请咨询合格专业人士或当地紧急支持渠道。"
    ),
    "unsafe": "我不能协助违法、欺骗、入侵或伤害他人的请求。",
    "too_long": "这次输入太长了，请缩短到更聚焦的问题后再发送。",
}


def _matches(patterns: list[str], text: str) -> tuple[str, ...]:
    hits: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(pattern)
    return tuple(hits)


def _message_content_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_message_content_text(item) for item in value if item is not None)
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"]
        if isinstance(value.get("content"), (str, list, dict)):
            return _message_content_text(value["content"])
    text = getattr(value, "text", None)
    if isinstance(text, str):
        return text
    content = getattr(value, "content", None)
    if isinstance(content, (str, list, dict)):
        return _message_content_text(content)
    return json.dumps(value, ensure_ascii=False, default=str)


def _input_text(input_value: str | list[Any]) -> str:
    if isinstance(input_value, str):
        return input_value

    # The SDK may pass conversation input including prior history. Guardrails
    # should judge the current user turn, not re-scan older stored messages.
    for item in reversed(input_value):
        role = item.get("role") if isinstance(item, dict) else getattr(item, "role", None)
        if role == "user":
            content = item.get("content") if isinstance(item, dict) else getattr(item, "content", item)
            return _message_content_text(content)

    return json.dumps(input_value, ensure_ascii=False, default=str)


def input_check_from_tripwire(exc: Exception) -> InputCheckResult:
    """Recover a user-facing input guardrail result from an SDK tripwire."""

    guardrail_result = getattr(exc, "guardrail_result", None)
    output = getattr(guardrail_result, "output", None)
    output_info = getattr(output, "output_info", None)
    if isinstance(output_info, dict):
        issues: list[InputIssue] = []
        for item in output_info.get("issues") or []:
            if not isinstance(item, dict):
                continue
            matches = item.get("matches") or ()
            issues.append(
                InputIssue(
                    code=str(item.get("code") or "input_guardrail"),
                    category=str(item.get("category") or "input_guardrail"),
                    message=str(item.get("message") or "输入触发安全护栏。"),
                    severity=str(item.get("severity") or "block"),
                    matches=tuple(str(match) for match in matches),
                )
            )
        return InputCheckResult(
            allowed=False,
            issues=tuple(issues),
            response=output_info.get("response") or "这个请求无法按当前安全边界处理。",
        )

    return InputCheckResult(
        allowed=False,
        issues=(
            InputIssue(
                code="input_guardrail_tripwire",
                category="input_guardrail",
                message="输入触发安全护栏。",
            ),
        ),
        response="这个请求无法按当前安全边界处理。",
    )


def run_input_checks(
    message: str,
    *,
    max_chars: int | None = None,
) -> InputCheckResult:
    """Run deterministic checks and return a block/allow decision."""

    if not settings.input_guardrails_enabled:
        return InputCheckResult(allowed=True)

    limit = max_chars if max_chars is not None else settings.input_max_chars
    compact = message.strip()
    issues: list[InputIssue] = []

    if len(compact) > limit:
        issues.append(
            InputIssue(
                code="input_too_long",
                category="too_long",
                message=f"输入长度 {len(compact)} 超过上限 {limit}。",
            )
        )

    prompt_hits = _matches(PROMPT_INJECTION_PATTERNS, compact)
    if prompt_hits:
        issues.append(
            InputIssue(
                code="prompt_injection",
                category="prompt_injection",
                message="输入包含越狱、提示词泄露或绕过规则意图。",
                matches=prompt_hits,
            )
        )

    unsafe_hits = _matches(UNSAFE_PATTERNS, compact)
    if unsafe_hits:
        issues.append(
            InputIssue(
                code="unsafe_request",
                category="unsafe",
                message="输入包含违法、欺骗、入侵或伤害请求。",
                matches=unsafe_hits,
            )
        )

    high_stakes_hits = _matches(HIGH_STAKES_PATTERNS, compact)
    if high_stakes_hits:
        issues.append(
            InputIssue(
                code="high_stakes_request",
                category="high_stakes",
                message="输入请求高风险领域的确定性建议。",
                matches=high_stakes_hits,
            )
        )

    if not issues:
        return InputCheckResult(allowed=True)

    first_category = issues[0].category
    return InputCheckResult(
        allowed=False,
        issues=tuple(issues),
        response=_CATEGORY_RESPONSES.get(first_category, _CATEGORY_RESPONSES["high_stakes"]),
    )


@input_guardrail(name="wenjia_input_guardrail", run_in_parallel=False)
def wenjia_input_guardrail(_context: Any, _agent: Any, input_value: str | list[Any]):
    """SDK-facing input guardrail mirroring ``run_input_checks``."""

    result = run_input_checks(_input_text(input_value))
    return GuardrailFunctionOutput(
        output_info=result.to_trace_payload(),
        tripwire_triggered=result.blocked,
    )
