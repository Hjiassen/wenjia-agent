"""Profile and BaZi specialist Agent."""

from __future__ import annotations

from agents import Agent

from wenjia_agent.prompts import load_prompt
from wenjia_agent.runtime.config import settings
from wenjia_agent.tools.bazi_tools import PROFILE_TOOLS


profile_agent = Agent(
    name="ProfileAgent",
    handoff_description="用于收集出生资料、查询出生地、完成确定性八字排盘。",
    instructions=load_prompt("profile_agent.md"),
    model=settings.openai_agent_model,
    tools=PROFILE_TOOLS,
)
