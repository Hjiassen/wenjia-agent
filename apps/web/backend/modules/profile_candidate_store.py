"""Account-owned pending person suggestions, separate from formal profiles."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, create_engine, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from wenjia_agent.runtime.config import settings


class Base(DeclarativeBase):
    pass


class ProfileCandidate(Base):
    __tablename__ = "wenjia_profile_candidates"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "source_session_id",
            "normalized_name",
            "normalized_relationship",
            name="uq_profile_candidate_source",
        ),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True, nullable=False)
    display_name = Column(String(64), nullable=False)
    normalized_name = Column(String(64), nullable=False)
    suggested_relationship = Column(String(40), nullable=True)
    normalized_relationship = Column(String(40), nullable=False, default="")
    relationship_type = Column(String(20), nullable=True)
    custom_relationship = Column(String(40), nullable=True)
    status = Column(String(16), nullable=False, default="pending", index=True)
    source_session_id = Column(String(128), nullable=False, default="")
    source_message_id = Column(String(128), nullable=True)
    converted_profile_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    last_mentioned_at = Column(DateTime, nullable=False)


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


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize(value: str | None) -> str:
    return "".join((value or "").strip().lower().split())


def _iso(value: datetime) -> str:
    return f"{value.isoformat()}Z"


def _serialize(row: ProfileCandidate) -> dict[str, Any]:
    return {
        "id": row.id,
        "display_name": row.display_name,
        "suggested_relationship": row.suggested_relationship,
        "relationship_type": row.relationship_type,
        "custom_relationship": row.custom_relationship,
        "status": row.status,
        "source_session_id": row.source_session_id or None,
        "source_message_id": row.source_message_id,
        "converted_profile_id": row.converted_profile_id,
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
        "last_mentioned_at": _iso(row.last_mentioned_at),
    }


def list_candidates(user_id: int, *, status: str = "pending") -> list[dict[str, Any]]:
    init_db()
    with _Session() as db:
        query = select(ProfileCandidate).where(ProfileCandidate.user_id == user_id)
        if status != "all":
            query = query.where(ProfileCandidate.status == status)
        rows = db.execute(query.order_by(ProfileCandidate.last_mentioned_at.desc())).scalars().all()
        return [_serialize(row) for row in rows]


def create_candidate(user_id: int, data: dict[str, Any]) -> dict[str, Any]:
    init_db()
    now = _now()
    name = str(data.get("display_name") or "").strip()
    relationship = str(data.get("suggested_relationship") or "").strip()
    session_id = str(data.get("source_session_id") or "").strip()
    with _Session() as db:
        row = db.execute(
            select(ProfileCandidate).where(
                ProfileCandidate.user_id == user_id,
                ProfileCandidate.source_session_id == session_id,
                ProfileCandidate.normalized_name == _normalize(name),
                ProfileCandidate.normalized_relationship == _normalize(relationship),
            )
        ).scalar_one_or_none()
        if row is not None:
            row.last_mentioned_at = now
            row.updated_at = now
            if row.status == "dismissed":
                row.status = "pending"
            db.commit()
            db.refresh(row)
            return _serialize(row)

        row = ProfileCandidate(
            user_id=user_id,
            display_name=name,
            normalized_name=_normalize(name),
            suggested_relationship=relationship or None,
            normalized_relationship=_normalize(relationship),
            status="pending",
            source_session_id=session_id,
            source_message_id=data.get("source_message_id") or None,
            created_at=now,
            updated_at=now,
            last_mentioned_at=now,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _serialize(row)


def update_candidate(user_id: int, candidate_id: int, data: dict[str, Any]) -> dict[str, Any]:
    init_db()
    with _Session() as db:
        row = db.execute(
            select(ProfileCandidate).where(
                ProfileCandidate.id == candidate_id,
                ProfileCandidate.user_id == user_id,
                ProfileCandidate.status == "pending",
            )
        ).scalar_one_or_none()
        if row is None:
            raise LookupError("candidate not found")
        row.display_name = str(data.get("display_name") or "").strip()
        row.normalized_name = _normalize(row.display_name)
        row.relationship_type = data.get("relationship_type") or None
        row.custom_relationship = data.get("custom_relationship") or None
        row.updated_at = _now()
        db.commit()
        db.refresh(row)
        return _serialize(row)


def set_status(
    user_id: int,
    candidate_id: int,
    status: str,
    *,
    converted_profile_id: int | None = None,
) -> dict[str, Any]:
    if status not in {"pending", "dismissed", "converted"}:
        raise ValueError("invalid candidate status")
    init_db()
    with _Session() as db:
        row = db.execute(
            select(ProfileCandidate).where(
                ProfileCandidate.id == candidate_id,
                ProfileCandidate.user_id == user_id,
            )
        ).scalar_one_or_none()
        if row is None:
            raise LookupError("candidate not found")
        row.status = status
        row.converted_profile_id = converted_profile_id
        row.updated_at = _now()
        db.commit()
        db.refresh(row)
        return _serialize(row)


def convert_candidate(
    user_id: int,
    candidate_id: int,
    data: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create a formal profile and convert its candidate in one transaction."""

    from apps.web.backend.modules import profile_store

    init_db()
    profile_store.init_db()
    now = _now()
    name = str(data.get("name") or "").strip()
    relationship = str(data.get("relationship_type") or "").strip()
    if not name:
        raise ValueError("name is required")

    with _Session() as db:
        candidate = db.execute(
            select(ProfileCandidate).where(
                ProfileCandidate.id == candidate_id,
                ProfileCandidate.user_id == user_id,
                ProfileCandidate.status == "pending",
            )
        ).scalar_one_or_none()
        if candidate is None:
            raise LookupError("candidate not found")

        profile_store._check_relationship(db, user_id, relationship)  # noqa: SLF001
        profile = profile_store.UserProfile(
            user_id=user_id,
            source_session_id=candidate.source_session_id or None,
            name=name,
            relationship_type=relationship,
            custom_relationship=data.get("custom_relationship"),
            created_at=now,
            updated_at=now,
        )
        profile_store._apply_data(profile, data)  # noqa: SLF001
        db.add(profile)
        db.flush()

        candidate.status = "converted"
        candidate.converted_profile_id = profile.id
        candidate.updated_at = now
        db.commit()
        db.refresh(candidate)
        db.refresh(profile)
        return _serialize(candidate), profile_store._serialize(profile)  # noqa: SLF001
