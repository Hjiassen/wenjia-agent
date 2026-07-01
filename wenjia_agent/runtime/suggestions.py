"""Lightweight next-question suggestions for the web chat."""

from __future__ import annotations

import asyncio
import json
import logging
import re

from pydantic import BaseModel, Field, ValidationError

from wenjia_agent.runtime.config import settings
from wenjia_agent.runtime.models import build_openai_client

_SUGGESTION_TIMEOUT_SECONDS = 18.0
_MAX_USER_CHARS = 1200
_MAX_ASSISTANT_CHARS = 2400
logger = logging.getLogger(__name__)


class SuggestedQuestion(BaseModel):
    """One follow-up question suggestion shown in the chat UI."""

    prompt: str = Field(..., min_length=1, max_length=120)


class _SuggestionPayload(BaseModel):
    suggestions: list[str | SuggestedQuestion] = Field(default_factory=list)


_SYSTEM_PROMPT = """你是命理问答产品中的下一步问题推荐器。
根据用户本轮问题和助手回答，生成用户可以直接点击发送的继续追问问题。

要求：
- 问题必须和本轮上下文强相关。
- 不要重复用户已经问过的问题。
- 优先引导用户补充信息、选择分析方向、继续深入。
- 生成 3 个问题。
- 必须使用用户口吻，像用户自己在提问。
- 必须是疑问句，不能是命令式文案。
- 不要以“请”“请帮我”“请引导我”“基于刚才”开头。
- 每个问题不超过 60 个中文字符，结尾用问号。
- 只返回 JSON，不要 Markdown，不要解释。

输出格式：
{"suggestions":["我的事业方向接下来适合怎么走？"]}
"""


def _trim(value: str, max_chars: int) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    return compact[:max_chars]


def _extract_json_object(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)

    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return stripped[start : end + 1]
    return stripped


def _parse_suggestions(text: str) -> list[SuggestedQuestion]:
    try:
        raw = json.loads(_extract_json_object(text))
        if isinstance(raw, list):
            raw = {"suggestions": raw}
        payload = _SuggestionPayload.model_validate(raw)
    except (ValidationError, json.JSONDecodeError, ValueError):
        return []

    suggestions: list[SuggestedQuestion] = []
    seen: set[str] = set()
    for item in payload.suggestions:
        prompt_text = item.prompt if isinstance(item, SuggestedQuestion) else item
        prompt = _normalize_user_question(prompt_text)
        if not prompt or prompt in seen:
            continue
        seen.add(prompt)
        suggestions.append(SuggestedQuestion(prompt=prompt))
        if len(suggestions) >= 3:
            break
    return suggestions


def _normalize_user_question(value: str) -> str:
    prompt = _trim(value, 90)
    if not prompt:
        return ""

    command_prefixes = (
        "请",
        "请帮我",
        "请引导我",
        "帮我",
        "基于刚才",
        "根据刚才",
        "继续",
    )
    if prompt.startswith(command_prefixes):
        return ""

    if prompt[-1] not in "？?":
        if any(marker in prompt for marker in ("什么", "哪些", "怎么", "如何", "是否", "能不能")):
            prompt = f"{prompt}？"
        else:
            return ""
    return prompt


def _fallback_suggestions(user_message: str, assistant_message: str) -> list[SuggestedQuestion]:
    text = f"{user_message} {assistant_message}"
    candidates: list[str] = []

    if any(keyword in text for keyword in ("出生", "生日", "时辰", "出生地", "档案")):
        candidates.append("我还需要补充哪些出生信息？")
    if any(keyword in text for keyword in ("事业", "职业", "工作", "职场")):
        candidates.append("我的事业方向接下来适合怎么走？")
    if any(keyword in text for keyword in ("财", "收入", "赚钱", "财富")):
        candidates.append("我的财运和收入节奏有什么需要注意的？")
    if any(keyword in text for keyword in ("感情", "关系", "伴侣", "婚恋")):
        candidates.append("我的关系相处上有什么需要注意的？")
    if any(keyword in text for keyword in ("起名", "名字", "取名")):
        candidates.append("起名前我还需要补充哪些信息？")

    candidates.extend(
        [
            "我接下来还可以从哪些方向继续问？",
            "刚才结论里最值得我继续关注的重点是什么？",
            "我还需要补充什么信息，分析才会更准确？",
        ]
    )

    suggestions: list[SuggestedQuestion] = []
    seen: set[str] = set()
    for prompt in candidates:
        if prompt in seen:
            continue
        seen.add(prompt)
        suggestions.append(SuggestedQuestion(prompt=prompt))
        if len(suggestions) >= 3:
            break
    return suggestions


async def _request_suggestions(
    user_message: str,
    assistant_message: str,
) -> list[SuggestedQuestion]:
    client = build_openai_client()
    response = await client.chat.completions.create(
        model=settings.openai_analysis_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "用户本轮问题：\n"
                    f"{_trim(user_message, _MAX_USER_CHARS)}\n\n"
                    "助手本轮回答：\n"
                    f"{_trim(assistant_message, _MAX_ASSISTANT_CHARS)}"
                ),
            },
        ],
        temperature=0.35,
        max_tokens=360,
    )
    content = response.choices[0].message.content or ""
    return _parse_suggestions(content)


async def generate_suggestions(
    session_id: str | None,
    user_message: str,
    assistant_message: str,
) -> list[SuggestedQuestion]:
    """Generate follow-up suggestions without affecting the main Agent session."""

    del session_id  # Reserved for future profile-aware recommendation.

    if not user_message.strip() or not assistant_message.strip():
        return []

    try:
        suggestions = await asyncio.wait_for(
            _request_suggestions(user_message, assistant_message),
            timeout=_SUGGESTION_TIMEOUT_SECONDS,
        )
        return suggestions or _fallback_suggestions(user_message, assistant_message)
    except Exception as exc:  # noqa: BLE001 - suggestions should never break chat.
        logger.warning("Suggestion generation failed, using fallback: %s", exc)
        return _fallback_suggestions(user_message, assistant_message)
