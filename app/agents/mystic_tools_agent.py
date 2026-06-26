"""Deterministic lookup and tool-routing Agent."""

from __future__ import annotations

from agents import Agent

from app.prompts import load_prompt
from app.runtime.config import settings
from app.tools.bazi_tools import BAZI_TOOLS


mystic_tools_agent = Agent(
    name="MysticToolsAgent",
    handoff_description="用于省市查询、命盘上下文字段解释和工具调用排障。",
    instructions=load_prompt("mystic_tools_agent.md"),
    model=settings.openai_agent_model,
    tools=BAZI_TOOLS,
)
