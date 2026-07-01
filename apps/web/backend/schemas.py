"""Request/response models for the web backend."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request payload for one chat turn."""

    message: str = Field(..., min_length=1, max_length=8000)
    session_id: str | None = Field(default=None, max_length=128)


class ChatResponse(BaseModel):
    """Response payload for one chat turn."""

    session_id: str
    output: str


class ProfilePayload(BaseModel):
    """Editable person profile fields from the web UI."""

    name: str = Field(..., min_length=1, max_length=64)
    relationship_type: str = Field(default="本人", min_length=1, max_length=20)
    gender: str | None = Field(default=None, max_length=10)
    birth_year: int | None = Field(default=None, ge=1, le=9999)
    birth_month: int | None = Field(default=None, ge=1, le=12)
    birth_day: int | None = Field(default=None, ge=1, le=31)
    birth_hour: int | None = Field(default=None, ge=0, le=23)
    birth_minute: int | None = Field(default=None, ge=0, le=59)
    calendar_type: str | None = Field(default=None, max_length=10)
    is_leap_month: bool | None = None
    province: str | None = Field(default=None, max_length=50)
    city: str | None = Field(default=None, max_length=50)
    longitude: str | None = Field(default=None, max_length=20)
