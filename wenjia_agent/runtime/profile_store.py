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
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from wenjia_agent.runtime.config import settings
from wenjia_agent.runtime import memory_store


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
        "birth": {
            "year": profile.birth_year,
            "month": profile.birth_month,
            "day": profile.birth_day,
            "hour": profile.birth_hour,
            "minute": profile.birth_minute,
            "calendar_type": profile.calendar_type,
            "is_leap_month": bool(profile.is_leap_month)
            if profile.is_leap_month is not None
            else None,
            "province": profile.province,
            "city": profile.city,
            "longitude": profile.longitude,
        },
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
    user_id: str | None = None,
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
        summary = _summarize(profile)

    if user_id:
        try:
            memory_store.remember_profile(
                user_id,
                relationship_type,
                bazi,
                context,
                source_session_id=session_id,
            )
        except Exception:
            # Long-term memory is best-effort; never break a deterministic chart.
            pass
    return summary


def upsert_manual_profile(
    session_id: str,
    data: dict[str, Any],
    profile_id: int | None = None,
) -> dict[str, Any]:
    """Create or edit a person profile from explicit user input.

    Manual edits preserve existing computed BaZi fields unless the user changes
    birth/calendar/location fields, because those changes make old pillars
    potentially stale.
    """

    init_db()
    now = datetime.now(UTC).replace(tzinfo=None)
    name = str(data.get("name") or "").strip()
    if not name:
        raise ValueError("name is required")

    birth_fields = (
        "birth_year",
        "birth_month",
        "birth_day",
        "birth_hour",
        "birth_minute",
        "calendar_type",
        "is_leap_month",
        "province",
        "city",
        "longitude",
    )

    with _Session() as db:  # type: Session
        profile: Profile | None = None
        if profile_id is not None:
            profile = db.get(Profile, profile_id)
            if profile is None or profile.session_id != session_id:
                raise LookupError("profile not found")
        if profile is None:
            profile = Profile(session_id=session_id, created_at=now)
            db.add(profile)

        birth_changed = any(getattr(profile, field) != data.get(field) for field in birth_fields)

        profile.name = name
        profile.relationship_type = str(data.get("relationship_type") or "本人").strip() or "本人"
        profile.gender = data.get("gender") or None
        profile.birth_year = data.get("birth_year")
        profile.birth_month = data.get("birth_month")
        profile.birth_day = data.get("birth_day")
        profile.birth_hour = data.get("birth_hour")
        profile.birth_minute = data.get("birth_minute")
        profile.calendar_type = data.get("calendar_type") or None
        leap = data.get("is_leap_month")
        profile.is_leap_month = int(leap) if leap is not None else None
        profile.province = data.get("province") or None
        profile.city = data.get("city") or None
        longitude = data.get("longitude")
        profile.longitude = str(longitude) if longitude not in (None, "") else None

        if birth_changed:
            profile.year_pillar = None
            profile.month_pillar = None
            profile.day_pillar = None
            profile.hour_pillar = None
            profile.five_elements = None
            profile.bazi_json = None
            profile.context_json = None

        profile.updated_at = now
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
