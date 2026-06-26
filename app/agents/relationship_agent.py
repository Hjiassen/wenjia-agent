"""Relationship and compatibility Agent."""

from __future__ import annotations

from agents import Agent

from app.domain.schemas import RelationshipReport
from app.prompts import load_prompt
from app.runtime.config import settings
from app.tools.bazi_tools import BAZI_TOOLS


relationship_agent = Agent(
    name="RelationshipAgent",
    handoff_description="用于两人或多人关系、合盘、沟通模式与相处建议分析。",
    instructions=load_prompt("relationship_agent.md"),
    model=settings.openai_analysis_model,
    tools=BAZI_TOOLS,
    output_type=RelationshipReport,
)
