"""Dedicated persistence for conversation person profiles (人物档案).

Profiles are keyed by ``session_id`` — this project has no account system (see
``AgentContext`` in app/domain/schemas.py). A single conversation can hold
several people (本人/父亲/母亲/…) distinguished by ``relationship_type``, which the
naming Agent reuses to factor parents' BaZi into suggestions.

We open our own synchronous SQLAlchemy engine on the *same* sqlite file the SDK
uses for session memory; the two manage independent tables. Tool functions run
synchronously, so a sync session is the natural fit.
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
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.runtime.config import settings


class Base(DeclarativeBase):
    pass


class Profile(Base):
    """A person profile attached to a conversation."""

    __tablename__ = "wenjia_profiles"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(128), index=True, nullable=False)
    relationship_type = Column(String(20), nullable=False, default="本人")
    name = Column(String(64), nullable=False)
    gender = Column(String(10), nullable=True)

    birth_year = Column(Integer, nullable=True)
    birth_month = Column(Integer, nullable=True)
    birth_day = Column(Integer, nullable=True)
    birth_hour = Column(Integer, nullable=True)
    birth_minute = Column(Integer, nullable=True)
    calendar_type = Column(String(10), nullable=True)
    is_leap_month = Column(Integer, nullable=True)
    province = Column(String(50), nullable=True)
    city = Column(String(50), nullable=True)
    longitude = Column(String(20), nullable=True)

    year_pillar = Column(String(10), nullable=True)
    month_pillar = Column(String(10), nullable=True)
    day_pillar = Column(String(10), nullable=True)
    hour_pillar = Column(String(10), nullable=True)
    five_elements = Column(Text, nullable=True)

    bazi_json = Column(Text, nullable=True)
    context_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)


def _sync_db_url() -> str:
    """Derive a synchronous sqlite URL from the async session DB URL."""

    return settings.session_db_url.replace("+aiosqlite", "")


_engine = create_engine(_sync_db_url(), future=True)
_Session = sessionmaker(bind=_engine, future=True)
_initialized = False


def init_db() -> None:
    """Create the profiles table if needed (idempotent)."""

    global _initialized
    if _initialized:
        return
    Base.metadata.create_all(_engine)
    _initialized = True


def _summarize(profile: Profile) -> dict[str, Any]:
    """Compact, model-friendly view of a stored profile."""

    return {
        "id": profile.id,
        "name": profile.name,
        "relationship_type": profile.relationship_type,
        "gender": profile.gender,
        "pillars": {
            "year": profile.year_pillar,
            "month": profile.month_pillar,
            "day": profile.day_pillar,
            "hour": profile.hour_pillar,
        },
        "five_elements": json.loads(profile.five_elements) if profile.five_elements else None,
    }


def save_profile(
    session_id: str,
    relationship_type: str,
    bazi: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Upsert a profile by (session_id, relationship_type, name).

    Re-charting the same person updates the existing row instead of piling up
    duplicates. ``bazi`` is a ``BaziResult`` dump; ``context`` a ``BaziContext`` dump.
    """

    init_db()
    name = str(bazi.get("name") or context.get("profile_name") or "未命名")
    now = datetime.now(UTC).replace(tzinfo=None)
    pillars = context.get("pillars") or {}

    with _Session() as db:  # type: Session
        existing = db.execute(
            select(Profile).where(
                Profile.session_id == session_id,
                Profile.relationship_type == relationship_type,
                Profile.name == name,
            )
        ).scalar_one_or_none()

        profile = existing or Profile(
            session_id=session_id,
            relationship_type=relationship_type,
            name=name,
            created_at=now,
        )

        profile.gender = bazi.get("gender")
        profile.calendar_type = bazi.get("input_calendar_type") or context.get("calendar_type")
        longitude = bazi.get("longitude")
        profile.longitude = str(longitude) if longitude is not None else None
        profile.year_pillar = bazi.get("year_pillar") or pillars.get("year")
        profile.month_pillar = bazi.get("month_pillar") or pillars.get("month")
        profile.day_pillar = bazi.get("day_pillar") or pillars.get("day")
        profile.hour_pillar = bazi.get("hour_pillar") or pillars.get("hour")
        profile.five_elements = json.dumps(bazi.get("five_elements") or {}, ensure_ascii=False)
        profile.bazi_json = json.dumps(bazi, ensure_ascii=False)
        profile.context_json = json.dumps(context, ensure_ascii=False)
        profile.updated_at = now

        if existing is None:
            db.add(profile)
        db.commit()
        db.refresh(profile)
        return _summarize(profile)


def list_profiles(session_id: str) -> list[dict[str, Any]]:
    """Return compact summaries of all profiles stored for a conversation."""

    init_db()
    with _Session() as db:  # type: Session
        rows = (
            db.execute(
                select(Profile)
                .where(Profile.session_id == session_id)
                .order_by(Profile.id)
            )
            .scalars()
            .all()
        )
        return [_summarize(row) for row in rows]
