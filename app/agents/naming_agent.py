"""Naming suggestion Agent."""

from __future__ import annotations

from agents import Agent

from app.domain.schemas import NamingReport
from app.prompts import load_prompt
from app.runtime.config import settings
from app.tools.bazi_tools import NAMING_TOOLS


naming_agent = Agent(
    name="NamingAgent",
    handoff_description="用于基于八字五行策略生成中文起名建议和筛选清单。",
    instructions=load_prompt("naming_agent.md"),
    model=settings.openai_analysis_model,
    tools=NAMING_TOOLS,
    output_type=NamingReport,
)
