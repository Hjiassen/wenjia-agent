"""Shared Pydantic schemas for wenjia-agent."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentContext(BaseModel):
    """Runtime context for a pure Agent module.

    The project deliberately has no account, auth, payment, order, or membership
    fields. External applications can pass their own session/profile IDs when
    embedding the Agent.
    """

    session_id: str | None = None
    profile_id: str | None = None
    locale: str = "zh-CN"
    source: str = "cli"
    regenerate: bool = False


class BirthInfo(BaseModel):
    """Birth data used by deterministic BaZi tools."""

    name: str = Field(..., description="Name or display label for the profile.")
    gender: str = Field(..., description="Gender text, for example 男/女/未知.")
    birth_year: int
    birth_month: int = Field(..., ge=1, le=12)
    birth_day: int = Field(..., ge=1, le=31)
    birth_hour: int = Field(..., ge=0, le=23)
    birth_minute: int = Field(default=0, ge=0, le=59)
    calendar_type: Literal["solar", "lunar"] = "solar"
    is_leap_month: bool = False
    province: str | None = None
    city: str | None = None
    longitude: float | None = None


class BaziResult(BaseModel):
    """Normalized output from the deterministic BaZi core."""

    name: str
    gender: str
    birth_year: int | None = None
    birth_month: int | None = None
    birth_day: int | None = None
    birth_hour: int | None = None
    birth_minute: int | None = None
    is_leap_month: bool | None = None
    province: str | None = None
    city: str | None = None
    input_calendar_type: str
    actual_birth_year: int
    actual_birth_month: int
    actual_birth_day: int
    longitude: float
    warnings: list[str] = Field(default_factory=list)

    year_pillar: str
    month_pillar: str
    day_pillar: str
    hour_pillar: str
    solar_year: int | None = None
    solar_month: int | None = None
    solar_day: int | None = None
    solar_hour: int | None = None
    solar_minute: int | None = None
    five_elements: dict[str, int]
    ten_gods: dict[str, Any] | None = None
    nayin: dict[str, Any] | None = None
    shen_sha: dict[str, Any] | None = None
    kong_wang: dict[str, Any] | None = None
    tai_yuan: str | None = None
    tai_yuan_nayin: str | None = None
    ming_gong: str | None = None
    ming_gong_nayin: str | None = None
    shen_gong: str | None = None
    shen_gong_nayin: str | None = None
    tai_xi: str | None = None
    tai_xi_nayin: str | None = None


class ToolResult(BaseModel):
    """Unified tool result envelope."""

    ok: bool
    tool_name: str
    data: dict[str, Any] | list[Any] | str | None = None
    message: str | None = None
    warnings: list[str] = Field(default_factory=list)


class CityListResult(BaseModel):
    """Province/city lookup result."""

    provinces: list[str] | None = None
    cities: list[str] | None = None


class ElementBalance(BaseModel):
    """Deterministic five-element balance summary."""

    counts: dict[str, int]
    dominant_elements: list[str] = Field(default_factory=list)
    weak_elements: list[str] = Field(default_factory=list)
    missing_elements: list[str] = Field(default_factory=list)
    total_count: int
    average_count: float


class BaziContext(BaseModel):
    """Agent-facing deterministic context built from a BaZi result."""

    profile_name: str
    gender: str
    calendar_type: str
    actual_solar_date: str
    true_solar_time: str | None = None
    longitude: float
    pillars: dict[str, str]
    five_element_balance: ElementBalance
    ten_gods: dict[str, Any] | None = None
    nayin: dict[str, Any] | None = None
    shen_sha: dict[str, Any] | None = None
    kong_wang: dict[str, Any] | None = None
    life_palaces: dict[str, str | None] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class AnalysisSection(BaseModel):
    """Reusable section for Agent-generated reports."""

    title: str
    summary: str
    deterministic_basis: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class FortuneReport(BaseModel):
    """Structured output target for a fortune analysis Agent."""

    report_title: str
    profile_name: str
    bazi_summary: list[str] = Field(default_factory=list)
    sections: list[AnalysisSection] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    boundary_note: str = "命理内容仅作文化娱乐与个人参考。"


class RelationshipReport(BaseModel):
    """Structured output target for relationship and compatibility analysis."""

    report_title: str
    subject_names: list[str] = Field(default_factory=list)
    shared_basis: list[str] = Field(default_factory=list)
    sections: list[AnalysisSection] = Field(default_factory=list)
    communication_suggestions: list[str] = Field(default_factory=list)
    boundary_note: str = "关系分析仅作文化娱乐与沟通参考，不替代现实沟通。"


class NamingSuggestion(BaseModel):
    """One name suggestion and its reasoning."""

    name: str
    pinyin: str | None = None
    element_focus: list[str] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class NamingReport(BaseModel):
    """Structured output target for naming suggestions."""

    report_title: str
    profile_name: str
    element_strategy: list[str] = Field(default_factory=list)
    parent_references: list[str] = Field(
        default_factory=list,
        description="可选：参与起名参考的父母八字摘要，如『父亲 甲子 乙丑 丙寅 丁卯』。",
    )
    suggestions: list[NamingSuggestion] = Field(default_factory=list)
    screening_checklist: list[str] = Field(default_factory=list)
    boundary_note: str = "起名建议仅作文化审美与命理参考，最终应结合家庭偏好与现实使用场景。"
