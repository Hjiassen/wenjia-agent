"""Request/response models for the web backend."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RelationshipType = Literal["本人", "父亲", "母亲", "伴侣", "子女", "朋友", "其他"]


class AuthCredentials(BaseModel):
    """Username/password payload used by login."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8, max_length=128)


class RegisterCredentials(AuthCredentials):
    """Credentials required to create an account, including confirmation."""

    confirm_password: str = Field(..., min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterCredentials":
        if self.password != self.confirm_password:
            raise ValueError("passwords do not match")
        return self


class MemoryPayload(BaseModel):
    """User-managed non-profile long-term memory."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(default="note", min_length=1, max_length=32)
    key: str = Field(..., min_length=1, max_length=160)
    title: str = Field(..., min_length=1, max_length=120)
    content: str = Field(..., min_length=1, max_length=4000)
    payload: dict | None = None
    source_session_id: str | None = Field(default=None, max_length=128)


class ChatRequest(BaseModel):
    """Request payload for one chat turn."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., min_length=1, max_length=8000)
    session_id: str | None = Field(default=None, max_length=128)
    profile_ids: list[int] = Field(default_factory=list, max_length=8)


class ChatResponse(BaseModel):
    """Response payload for one chat turn."""

    session_id: str
    output: str


class SuggestionRequest(BaseModel):
    """Request payload for next-question suggestions."""

    session_id: str | None = Field(default=None, max_length=128)
    user_message: str = Field(..., min_length=1, max_length=8000)
    assistant_message: str = Field(..., min_length=1, max_length=12000)


class SuggestionResponse(BaseModel):
    """Response payload for next-question suggestions."""

    suggestions: list[str]


class ProfilePayload(BaseModel):
    """Editable person profile fields from the web UI."""

    name: str = Field(..., min_length=1, max_length=64)
    relationship_type: RelationshipType = "本人"
    custom_relationship: str | None = Field(default=None, max_length=40)
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
    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("name is required")
        return clean

    @model_validator(mode="after")
    def validate_custom_relationship(self) -> "ProfilePayload":
        custom = (self.custom_relationship or "").strip()
        if self.relationship_type == "其他" and not custom:
            raise ValueError("custom_relationship is required for 其他")
        self.custom_relationship = custom or None
        return self


class ProfileCandidatePayload(BaseModel):
    """User-confirmed pending-person suggestion from a conversation."""

    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(..., min_length=1, max_length=64)
    suggested_relationship: str | None = Field(default=None, max_length=40)
    source_session_id: str | None = Field(default=None, max_length=128)
    source_message_id: str | None = Field(default=None, max_length=128)

    @field_validator("display_name")
    @classmethod
    def display_name_must_not_be_blank(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("display_name is required")
        return clean


class ProfileCandidateUpdate(BaseModel):
    """Editable candidate fields before conversion."""

    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(..., min_length=1, max_length=64)
    relationship_type: RelationshipType | None = None
    custom_relationship: str | None = Field(default=None, max_length=40)

    @field_validator("display_name")
    @classmethod
    def candidate_name_must_not_be_blank(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("display_name is required")
        return clean

    @model_validator(mode="after")
    def validate_candidate_relationship(self) -> "ProfileCandidateUpdate":
        custom = (self.custom_relationship or "").strip()
        if self.relationship_type == "其他" and not custom:
            raise ValueError("custom_relationship is required for 其他")
        self.custom_relationship = custom or None
        return self


class ProfileCandidateConvertPayload(ProfilePayload):
    """Confirmed profile fields used to convert one pending candidate."""
