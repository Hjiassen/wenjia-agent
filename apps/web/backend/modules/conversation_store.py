"""Account-owned conversation persistence for the web application."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
from sqlalchemy import create_engine

from wenjia_agent.runtime.config import settings


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "wenjia_conversations"

    id = Column(String(128), primary_key=True)
    user_id = Column(Integer, index=True, nullable=False)
    title = Column(String(160), nullable=False, default="新的对话")
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    messages = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.sequence",
    )


class ConversationMessage(Base):
    __tablename__ = "wenjia_conversation_messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(
        String(128), ForeignKey("wenjia_conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sequence = Column(Integer, nullable=False)
    role = Column(String(16), nullable=False)
    body = Column(Text, nullable=False)
    payload = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, nullable=False)
    conversation = relationship("Conversation", back_populates="messages")


def _sync_db_url() -> str:
    return settings.session_db_url.replace("+aiosqlite", "")


_engine = create_engine(_sync_db_url(), future=True)
_Session = sessionmaker(bind=_engine, future=True)
_initialized = False


def init_db() -> None:
    global _initialized
    if _initialized:
        return
    Base.metadata.create_all(_engine)
    _initialized = True


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _iso(value: datetime) -> str:
    return f"{value.isoformat()}Z"


def _decode_payload(value: str) -> dict[str, Any]:
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _message_dict(message: ConversationMessage) -> dict[str, Any]:
    payload = _decode_payload(message.payload)
    return {
        "role": message.role,
        "body": message.body,
        "createdAt": _iso(message.created_at),
        **payload,
    }


def _title_for(messages: list[ConversationMessage]) -> str:
    first_user = next((item for item in messages if item.role == "user"), None)
    if first_user is None:
        return "新的对话"
    compact = " ".join(first_user.body.split())
    return f"{compact[:24]}..." if len(compact) > 24 else compact


def _summary(conversation: Conversation) -> dict[str, Any]:
    last = conversation.messages[-1] if conversation.messages else None
    preview = "还没有消息"
    if last is not None:
        compact = " ".join(last.body.split())
        preview = f"{compact[:36]}..." if len(compact) > 36 else compact
    return {
        "id": conversation.id,
        "title": conversation.title,
        "createdAt": _iso(conversation.created_at),
        "updatedAt": _iso(conversation.updated_at),
        "preview": preview or "还没有消息",
        "messageCount": len(conversation.messages),
    }


def list_conversations(user_id: int) -> list[dict[str, Any]]:
    init_db()
    with _Session() as db:
        rows = db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        ).scalars().all()
        return [_summary(row) for row in rows]


def get_conversation(user_id: int, conversation_id: str) -> dict[str, Any] | None:
    init_db()
    with _Session() as db:
        row = db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return {
            **_summary(row),
            "messages": [_message_dict(message) for message in row.messages],
        }


def can_access(user_id: int, conversation_id: str) -> bool:
    """Return whether a conversation is new or already owned by this user."""

    init_db()
    with _Session() as db:
        row = db.execute(
            select(Conversation.user_id).where(Conversation.id == conversation_id)
        ).scalar_one_or_none()
        return row is None or row == user_id


def append_message(
    user_id: int,
    conversation_id: str,
    role: str,
    body: str,
    *,
    payload: dict[str, Any] | None = None,
    created_at: datetime | None = None,
) -> None:
    if role not in {"user", "assistant"}:
        raise ValueError("invalid conversation message role")
    init_db()
    now = created_at or _utcnow()
    with _Session() as db:
        conversation = db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        ).scalar_one_or_none()
        if conversation is None:
            conversation = Conversation(
                id=conversation_id,
                user_id=user_id,
                title="新的对话",
                created_at=now,
                updated_at=now,
            )
            db.add(conversation)
            db.flush()
        sequence = len(conversation.messages)
        db.add(
            ConversationMessage(
                conversation_id=conversation_id,
                sequence=sequence,
                role=role,
                body=body,
                payload=json.dumps(payload or {}, ensure_ascii=False),
                created_at=now,
            )
        )
        conversation.updated_at = now
        db.flush()
        conversation.title = _title_for(conversation.messages)
        db.commit()


def update_latest_assistant_suggestions(
    user_id: int,
    conversation_id: str,
    assistant_body: str,
    suggestions: list[dict[str, str]],
) -> bool:
    init_db()
    with _Session() as db:
        conversation = db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        ).scalar_one_or_none()
        if conversation is None:
            return False
        target = next(
            (item for item in reversed(conversation.messages)
             if item.role == "assistant" and item.body == assistant_body),
            None,
        )
        if target is None:
            return False
        payload = _decode_payload(target.payload)
        payload["suggestions"] = suggestions
        target.payload = json.dumps(payload, ensure_ascii=False)
        conversation.updated_at = _utcnow()
        db.commit()
        return True


def delete_conversation(user_id: int, conversation_id: str) -> bool:
    init_db()
    with _Session() as db:
        conversation = db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        ).scalar_one_or_none()
        if conversation is None:
            return False
        db.delete(conversation)
        db.commit()
        return True


def clear_conversations(user_id: int) -> int:
    init_db()
    with _Session() as db:
        rows = db.execute(select(Conversation).where(Conversation.user_id == user_id)).scalars().all()
        for conversation in rows:
            db.delete(conversation)
        db.commit()
        return len(rows)
