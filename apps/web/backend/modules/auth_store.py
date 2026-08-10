"""Persistent users and opaque server-side authentication sessions."""

from __future__ import annotations

import hashlib
import re
import secrets
import time
import unicodedata
from datetime import UTC, datetime, timedelta
from typing import Any

from pwdlib import PasswordHash
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from apps.web.backend.settings import settings as backend_settings
from wenjia_agent.runtime.config import settings as runtime_settings


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "wenjia_users"

    id = Column(Integer, primary_key=True)
    username_normalized = Column(String(64), unique=True, index=True, nullable=False)
    username_display = Column(String(64), nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    deleted_at = Column(DateTime, nullable=True)


class AuthSession(Base):
    __tablename__ = "wenjia_auth_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("wenjia_users.id"), index=True, nullable=False)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, index=True, nullable=False)
    last_seen_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)


def _sync_db_url() -> str:
    return runtime_settings.session_db_url.replace("+aiosqlite", "")


_engine = create_engine(_sync_db_url(), future=True)
_Session = sessionmaker(bind=_engine, future=True)
_initialized = False
_password_hash = PasswordHash.recommended()
_DUMMY_PASSWORD_HASH = _password_hash.hash("wenjia-dummy-password")
_USERNAME_PATTERN = re.compile(r"^[\w.\-\u4e00-\u9fff]+$", re.UNICODE)


class UsernameTakenError(ValueError):
    pass


class InvalidCredentialsError(ValueError):
    pass


_attempts: dict[str, list[float]] = {}


def check_rate_limit(identifier: str, *, limit: int = 8, window_seconds: int = 60) -> None:
    now = time.monotonic()
    recent = [stamp for stamp in _attempts.get(identifier, []) if now - stamp < window_seconds]
    if len(recent) >= limit:
        raise RuntimeError("too many authentication attempts; try again later")
    recent.append(now)
    _attempts[identifier] = recent


def clear_rate_limit(identifier: str) -> None:
    _attempts.pop(identifier, None)


def init_db() -> None:
    global _initialized
    if _initialized:
        return
    Base.metadata.create_all(_engine)
    _initialized = True


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize_username(username: str) -> tuple[str, str]:
    display = unicodedata.normalize("NFKC", username).strip()
    if not 3 <= len(display) <= 32 or not _USERNAME_PATTERN.fullmatch(display):
        raise ValueError("username must be 3-32 letters, numbers, dots, dashes, or underscores")
    return display.casefold(), display


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _summarize_user(user: User, *, include_password_hash: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": user.id,
        "username": user.username_display,
        "created_at": user.created_at.isoformat(),
    }
    if include_password_hash:
        result["password_hash"] = user.password_hash
    return result


def create_user(username: str, password: str) -> dict[str, Any]:
    init_db()
    normalized, display = _normalize_username(username)
    now = _utcnow()
    user = User(
        username_normalized=normalized,
        username_display=display,
        password_hash=_password_hash.hash(password),
        created_at=now,
        updated_at=now,
    )
    try:
        with _Session() as db:
            db.add(user)
            db.commit()
            db.refresh(user)
            return _summarize_user(user)
    except IntegrityError as exc:
        raise UsernameTakenError("username is already registered") from exc


def get_user_by_username(username: str) -> dict[str, Any] | None:
    init_db()
    normalized, _ = _normalize_username(username)
    with _Session() as db:
        user = db.execute(
            select(User).where(
                User.username_normalized == normalized,
                User.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        return _summarize_user(user, include_password_hash=True) if user else None


def authenticate_user(username: str, password: str) -> dict[str, Any]:
    try:
        user = get_user_by_username(username)
    except ValueError:
        user = None
    encoded = user["password_hash"] if user else _DUMMY_PASSWORD_HASH
    if not _password_hash.verify(password, encoded) or user is None:
        raise InvalidCredentialsError("invalid username or password")
    return {key: value for key, value in user.items() if key != "password_hash"}


def create_auth_session(user_id: int) -> str:
    init_db()
    token = secrets.token_urlsafe(32)
    now = _utcnow()
    with _Session() as db:
        db.add(
            AuthSession(
                user_id=user_id,
                token_hash=_token_hash(token),
                created_at=now,
                expires_at=now + timedelta(days=backend_settings.auth_session_days),
                last_seen_at=now,
            )
        )
        db.commit()
    return token


def resolve_auth_session(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    init_db()
    now = _utcnow()
    with _Session() as db:
        row = db.execute(
            select(AuthSession, User)
            .join(User, User.id == AuthSession.user_id)
            .where(
                AuthSession.token_hash == _token_hash(token),
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
                User.deleted_at.is_(None),
            )
        ).one_or_none()
        if row is None:
            return None
        auth_session, user = row
        auth_session.last_seen_at = now
        db.commit()
        return _summarize_user(user)


def revoke_auth_session(token: str | None) -> bool:
    if not token:
        return False
    init_db()
    with _Session() as db:
        auth_session = db.execute(
            select(AuthSession).where(AuthSession.token_hash == _token_hash(token))
        ).scalar_one_or_none()
        if auth_session is None:
            return False
        if auth_session.revoked_at is None:
            auth_session.revoked_at = _utcnow()
            db.commit()
        return True
