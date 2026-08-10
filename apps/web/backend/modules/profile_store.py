"""Account-owned person profiles with soft deletion."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from wenjia_agent.runtime.config import settings


class Base(DeclarativeBase):
    pass


class UserProfile(Base):
    __tablename__ = "wenjia_user_profiles"

    id = Column(Integer, primary_key=True)
    # Ownership is checked in the service layer. Keeping this module's metadata
    # independent allows it to migrate independently from the auth tables.
    user_id = Column(Integer, index=True, nullable=False)
    source_session_id = Column(String(128), nullable=True)
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
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    deleted_at = Column(DateTime, nullable=True)


def _sync_db_url() -> str:
    return settings.session_db_url.replace("+aiosqlite", "")


_engine = create_engine(_sync_db_url(), future=True)
_Session = sessionmaker(bind=_engine, future=True)
_initialized = False


class ProfileConflictError(ValueError):
    pass


def init_db() -> None:
    global _initialized
    if _initialized:
        return
    Base.metadata.create_all(_engine)
    _initialized = True


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _birth_changed(profile: UserProfile, data: dict[str, Any]) -> bool:
    return any(
        getattr(profile, field) != data.get(field)
        for field in (
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
    )


def _check_relationship(db, user_id: int, relationship_type: str, profile_id: int | None = None) -> None:
    if relationship_type != "本人":
        return
    query = select(UserProfile).where(
        UserProfile.user_id == user_id,
        UserProfile.relationship_type == "本人",
        UserProfile.deleted_at.is_(None),
    )
    if profile_id is not None:
        query = query.where(UserProfile.id != profile_id)
    if db.execute(query).scalar_one_or_none() is not None:
        raise ProfileConflictError("only one active 本人 profile is allowed")


def _serialize(profile: UserProfile) -> dict[str, Any]:
    return {
        "id": profile.id,
        "user_id": profile.user_id,
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
        "deleted_at": profile.deleted_at.isoformat() if profile.deleted_at else None,
        "created_at": profile.created_at.isoformat(),
        "updated_at": profile.updated_at.isoformat(),
    }


def list_profiles(user_id: int, *, include_deleted: bool = False) -> list[dict[str, Any]]:
    init_db()
    with _Session() as db:
        query = select(UserProfile).where(UserProfile.user_id == user_id)
        if not include_deleted:
            query = query.where(UserProfile.deleted_at.is_(None))
        rows = db.execute(query.order_by(UserProfile.id)).scalars().all()
        return [_serialize(row) for row in rows]


def get_profile(user_id: int, profile_id: int, *, include_deleted: bool = False) -> dict[str, Any]:
    init_db()
    with _Session() as db:
        profile = db.execute(
            select(UserProfile).where(
                UserProfile.id == profile_id,
                UserProfile.user_id == user_id,
                UserProfile.deleted_at.is_(None) if not include_deleted else True,
            )
        ).scalar_one_or_none()
        if profile is None:
            raise LookupError("profile not found")
        return _serialize(profile)


def get_profiles_by_ids(user_id: int, profile_ids: list[int]) -> list[dict[str, Any]]:
    """Return explicitly selected active profiles in the caller's order."""

    if not profile_ids:
        return []
    init_db()
    unique_ids = list(dict.fromkeys(profile_ids))
    with _Session() as db:
        rows = db.execute(
            select(UserProfile).where(
                UserProfile.user_id == user_id,
                UserProfile.id.in_(unique_ids),
                UserProfile.deleted_at.is_(None),
            )
        ).scalars().all()
        by_id = {row.id: row for row in rows}
        if len(by_id) != len(unique_ids):
            raise LookupError("profile not found")
        return [_serialize(by_id[profile_id]) for profile_id in unique_ids]


def create_profile(user_id: int, data: dict[str, Any], *, source_session_id: str | None = None) -> dict[str, Any]:
    init_db()
    now = _now()
    name = str(data.get("name") or "").strip()
    if not name:
        raise ValueError("name is required")
    relationship_type = str(data.get("relationship_type") or "本人").strip() or "本人"
    with _Session() as db:
        _check_relationship(db, user_id, relationship_type)
        profile = UserProfile(
            user_id=user_id,
            source_session_id=source_session_id,
            name=name,
            relationship_type=relationship_type,
            created_at=now,
            updated_at=now,
        )
        _apply_data(profile, data)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return _serialize(profile)


def update_profile(user_id: int, profile_id: int, data: dict[str, Any]) -> dict[str, Any]:
    init_db()
    now = _now()
    with _Session() as db:
        profile = db.execute(
            select(UserProfile).where(
                UserProfile.id == profile_id,
                UserProfile.user_id == user_id,
                UserProfile.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if profile is None:
            raise LookupError("profile not found")
        name = str(data.get("name") or "").strip()
        if not name:
            raise ValueError("name is required")
        relationship_type = str(data.get("relationship_type") or "本人").strip() or "本人"
        _check_relationship(db, user_id, relationship_type, profile_id)
        changed_birth = _birth_changed(profile, data)
        profile.name = name
        profile.relationship_type = relationship_type
        _apply_data(profile, data)
        if changed_birth:
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
        return _serialize(profile)


def save_computed_profile(
    user_id: int,
    relationship_type: str,
    bazi: dict[str, Any],
    context: dict[str, Any],
    *,
    source_session_id: str | None = None,
) -> dict[str, Any]:
    """Upsert a freshly calculated chart without touching long-term memory."""

    init_db()
    name = str(bazi.get("name") or context.get("profile_name") or "未命名").strip()
    relationship = str(relationship_type or "本人").strip() or "本人"
    now = _now()
    pillars = context.get("pillars") or {}
    with _Session() as db:
        profile = db.execute(
            select(UserProfile).where(
                UserProfile.user_id == user_id,
                UserProfile.relationship_type == relationship,
                UserProfile.name == name,
                UserProfile.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if profile is None:
            _check_relationship(db, user_id, relationship)
            profile = UserProfile(
                user_id=user_id,
                relationship_type=relationship,
                name=name,
                created_at=now,
                updated_at=now,
                source_session_id=source_session_id,
            )
            db.add(profile)
        profile.name = name
        profile.relationship_type = relationship
        profile.gender = bazi.get("gender") or None
        profile.birth_year = _to_int(bazi.get("birth_year") or bazi.get("actual_birth_year"))
        profile.birth_month = _to_int(bazi.get("birth_month") or bazi.get("actual_birth_month"))
        profile.birth_day = _to_int(bazi.get("birth_day") or bazi.get("actual_birth_day"))
        profile.birth_hour = _to_int(bazi.get("birth_hour") or bazi.get("solar_hour"))
        profile.birth_minute = _to_int(bazi.get("birth_minute") or bazi.get("solar_minute"))
        profile.calendar_type = bazi.get("input_calendar_type") or context.get("calendar_type")
        leap = bazi.get("is_leap_month")
        profile.is_leap_month = int(leap) if leap is not None else None
        profile.province = bazi.get("province") or None
        profile.city = bazi.get("city") or None
        longitude = bazi.get("longitude")
        profile.longitude = str(longitude) if longitude is not None else None
        profile.year_pillar = bazi.get("year_pillar") or pillars.get("year")
        profile.month_pillar = bazi.get("month_pillar") or pillars.get("month")
        profile.day_pillar = bazi.get("day_pillar") or pillars.get("day")
        profile.hour_pillar = bazi.get("hour_pillar") or pillars.get("hour")
        profile.five_elements = json.dumps(bazi.get("five_elements") or {}, ensure_ascii=False)
        profile.bazi_json = json.dumps(bazi, ensure_ascii=False)
        profile.context_json = json.dumps(context, ensure_ascii=False)
        profile.source_session_id = source_session_id or profile.source_session_id
        profile.updated_at = now
        db.commit()
        db.refresh(profile)
        return _serialize(profile)


def soft_delete_profile(user_id: int, profile_id: int) -> dict[str, Any]:
    init_db()
    with _Session() as db:
        profile = db.execute(
            select(UserProfile).where(UserProfile.id == profile_id, UserProfile.user_id == user_id)
        ).scalar_one_or_none()
        if profile is None:
            raise LookupError("profile not found")
        if profile.deleted_at is None:
            profile.deleted_at = _now()
            profile.updated_at = profile.deleted_at
            db.commit()
            db.refresh(profile)
        return _serialize(profile)


def restore_profile(user_id: int, profile_id: int) -> dict[str, Any]:
    init_db()
    with _Session() as db:
        profile = db.execute(
            select(UserProfile).where(
                UserProfile.id == profile_id,
                UserProfile.user_id == user_id,
                UserProfile.deleted_at.is_not(None),
            )
        ).scalar_one_or_none()
        if profile is None:
            raise LookupError("deleted profile not found")
        _check_relationship(db, user_id, profile.relationship_type, profile_id)
        profile.deleted_at = None
        profile.updated_at = _now()
        db.commit()
        db.refresh(profile)
        return _serialize(profile)


def _apply_data(profile: UserProfile, data: dict[str, Any]) -> None:
    for field in (
        "gender",
        "birth_year",
        "birth_month",
        "birth_day",
        "birth_hour",
        "birth_minute",
        "calendar_type",
        "province",
        "city",
    ):
        setattr(profile, field, data.get(field) or None)
    leap = data.get("is_leap_month")
    profile.is_leap_month = int(leap) if leap is not None else None
    longitude = data.get("longitude")
    profile.longitude = str(longitude) if longitude not in (None, "") else None


def _to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
