"""Conservative, suggestion-only detection of related people in user text."""

from __future__ import annotations

import hashlib
import re


_OPT_OUT = re.compile(r"(?:不要|不用|别|无需).{0,4}(?:记录|保存|建档|加入档案)")
_RELATION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("母亲", re.compile(r"(?:我(?:的)?(?:妈妈|母亲)|我妈)")),
    ("父亲", re.compile(r"(?:我(?:的)?(?:爸爸|父亲)|我爸)")),
    (
        "伴侣",
        re.compile(
            r"(?:我(?:的)?(?:对象|伴侣|老公|老婆|丈夫|妻子|男朋友|女朋友))"
        ),
    ),
    ("子女", re.compile(r"(?:我(?:的)?(?:儿子|女儿|孩子)|我的小孩)")),
    ("朋友", re.compile(r"(?:我(?:的)?朋友)")),
)


def detect_profile_candidates(message: str, session_id: str) -> list[dict[str, str]]:
    """Return up to three non-persistent relationship suggestions.

    Display names deliberately remain generic. A real name must be supplied by
    the user when converting the suggestion into a formal profile.
    """

    text = " ".join(message.strip().split())
    if not text or _OPT_OUT.search(text):
        return []

    suggestions: list[dict[str, str]] = []
    for relationship, pattern in _RELATION_PATTERNS:
        if not pattern.search(text):
            continue
        digest = hashlib.sha256(
            f"{session_id}:{relationship}:{text}".encode("utf-8")
        ).hexdigest()[:16]
        suggestions.append(
            {
                "key": f"profile-candidate:{digest}",
                "display_name": f"我的{relationship}",
                "suggested_relationship": relationship,
                "source_message_id": f"message:{digest}",
            }
        )
        if len(suggestions) == 3:
            break
    return suggestions
