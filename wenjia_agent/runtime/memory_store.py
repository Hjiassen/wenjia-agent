"""Long-term user memory storage.

This module stores compact facts keyed by an embedding app supplied ``user_id``
(``client_id`` in the web app). It intentionally does not create an account
system; the caller owns identity and consent.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from wenjia_agent.runtime.config import settings


class Base(DeclarativeBase):
    pass


class MemoryRecord(Base):
    """A compact long-term memory item for one caller-owned user id."""

    __tablename__ = "wenjia_memories"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_wenjia_memory_user_key"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(String(128), index=True, nullable=False)
    kind = Column(String(32), index=True, nullable=False)
    key = Column(String(160), nullable=False)
    title = Column(String(120), nullable=False)
    content = Column(Text, nullable=False)
    payload_json = Column(Text, nullable=True)
    source_session_id = Column(String(128), nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)


def _sync_db_url() -> str:
    return settings.session_db_url.replace("+aiosqlite", "")


_engine = create_engine(_sync_db_url(), future=True)
_Session = sessionmaker(bind=_engine, future=True)
_initialized = False


def init_db() -> None:
    """Create long-term memory tables if needed."""

    global _initialized
    if _initialized:
        return
    Base.metadata.create_all(_engine)
    _initialized = True


def _clean_user_id(user_id: str | None) -> str:
    return (user_id or "").strip()[:128]


def _summarize(row: MemoryRecord) -> dict[str, Any]:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "kind": row.kind,
        "key": row.key,
        "title": row.title,
        "content": row.content,
        "payload": json.loads(row.payload_json) if row.payload_json else None,
        "source_session_id": row.source_session_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def upsert_memory(
    user_id: str,
    *,
    kind: str,
    key: str,
    title: str,
    content: str,
    payload: dict[str, Any] | None = None,
    source_session_id: str | None = None,
) -> dict[str, Any]:
    """Create or update one long-term memory item."""

    clean_user_id = _clean_user_id(user_id)
    if not clean_user_id:
        raise ValueError("user_id is required")
    if not key.strip():
        raise ValueError("memory key is required")
    if not content.strip():
        raise ValueError("memory content is required")

    init_db()
    now = datetime.now(UTC).replace(tzinfo=None)
    clean_key = key.strip()[:160]

    with _Session() as db:
        record = db.execute(
            select(MemoryRecord).where(
                MemoryRecord.user_id == clean_user_id,
                MemoryRecord.key == clean_key,
            )
        ).scalar_one_or_none()

        if record is None:
            record = MemoryRecord(user_id=clean_user_id, key=clean_key, created_at=now)
            db.add(record)

        record.kind = kind.strip()[:32] or "note"
        record.title = title.strip()[:120] or record.kind
        record.content = content.strip()
        record.payload_json = json.dumps(payload, ensure_ascii=False) if payload is not None else None
        record.source_session_id = source_session_id
        record.updated_at = now
        db.commit()
        db.refresh(record)
        return _summarize(record)


def list_memories(
    user_id: str | None,
    *,
    kind: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """List recent long-term memories for a user id."""

    clean_user_id = _clean_user_id(user_id)
    if not clean_user_id or not settings.long_term_memory_enabled:
        return []

    init_db()
    max_items = limit if limit is not None else settings.long_term_memory_max_items
    with _Session() as db:
        stmt = select(MemoryRecord).where(MemoryRecord.user_id == clean_user_id)
        if kind is not None:
            stmt = stmt.where(MemoryRecord.kind == kind)
        rows = (
            db.execute(stmt.order_by(MemoryRecord.updated_at.desc(), MemoryRecord.id.desc()))
            .scalars()
            .all()
        )
        return [_summarize(row) for row in rows[:max(0, max_items)]]


def _birth_text(bazi: dict[str, Any]) -> str:
    parts: list[str] = []
    year = bazi.get("actual_birth_year") or bazi.get("birth_year")
    month = bazi.get("actual_birth_month") or bazi.get("birth_month")
    day = bazi.get("actual_birth_day") or bazi.get("birth_day")
    hour = bazi.get("birth_hour")
    minute = bazi.get("birth_minute")
    if year and month and day:
        time_text = ""
        if hour is not None:
            time_text = f" {int(hour):02d}:{int(minute or 0):02d}"
        parts.append(f"{year}-{int(month):02d}-{int(day):02d}{time_text}")
    calendar = bazi.get("input_calendar_type")
    if calendar:
        parts.append(str(calendar))
    place = "".join(str(item) for item in (bazi.get("province"), bazi.get("city")) if item)
    if place:
        parts.append(place)
    return "，".join(parts)


def _profile_memory_content(relationship_type: str, bazi: dict[str, Any], context: dict[str, Any]) -> str:
    name = str(bazi.get("name") or context.get("profile_name") or "未命名")
    gender = bazi.get("gender") or "未知"
    pillars = context.get("pillars") or {}
    pillar_text = " ".join(
        str(pillars.get(key) or bazi.get(f"{key}_pillar") or "")
        for key in ("year", "month", "day", "hour")
    ).strip()
    elements = bazi.get("five_elements") or {}
    element_text = "，".join(f"{key}{value}" for key, value in elements.items())
    parts = [f"{relationship_type}：{name}", f"性别{gender}"]
    birth = _birth_text(bazi)
    if birth:
        parts.append(f"出生{birth}")
    if pillar_text:
        parts.append(f"四柱{pillar_text}")
    if element_text:
        parts.append(f"五行{element_text}")
    return "；".join(parts)


def remember_profile(
    user_id: str | None,
    relationship_type: str,
    bazi: dict[str, Any],
    context: dict[str, Any],
    *,
    source_session_id: str | None = None,
) -> dict[str, Any] | None:
    """Persist a charted person as long-term memory."""

    clean_user_id = _clean_user_id(user_id)
    if not clean_user_id or not settings.long_term_memory_enabled:
        return None

    name = str(bazi.get("name") or context.get("profile_name") or "未命名")
    clean_relationship = relationship_type.strip() or "本人"
    key = f"profile:{clean_relationship}:{name}"
    content = _profile_memory_content(clean_relationship, bazi, context)
    return upsert_memory(
        clean_user_id,
        kind="profile",
        key=key,
        title=f"{clean_relationship}：{name}",
        content=content,
        payload={"relationship_type": clean_relationship, "bazi": bazi, "context": context},
        source_session_id=source_session_id,
    )


def format_memory_context(user_id: str | None, *, limit: int | None = None) -> str:
    """Format compact memories for injection into Agent instructions."""

    memories = list_memories(user_id, limit=limit)
    if not memories:
        return ""
    lines = [
        "长期记忆（由用户过往会话保存，仅在本轮问题相关时使用；若用户本轮更正，以最新输入为准）："
    ]
    lines.extend(f"- {item['title']}：{item['content']}" for item in memories)
    return "\n".join(lines)

