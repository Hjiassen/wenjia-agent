"""Main triage Agent."""

from __future__ import annotations

from agents import Agent

from wenjia_agent.agents.fortune_agent import fortune_agent
from wenjia_agent.agents.mystic_tools_agent import mystic_tools_agent
from wenjia_agent.agents.naming_agent import naming_agent
from wenjia_agent.agents.profile_agent import profile_agent
from wenjia_agent.agents.relationship_agent import relationship_agent
from wenjia_agent.prompts import load_prompt
from wenjia_agent.runtime.config import settings
from wenjia_agent.tools.bazi_tools import BAZI_TOOLS


main_agent = Agent(
    name="WenjiaMainAgent",
    instructions=load_prompt("main_agent.md"),
    model=settings.openai_agent_model,
    tools=BAZI_TOOLS,
    handoffs=[
        profile_agent,
        fortune_agent,
        relationship_agent,
        naming_agent,
        mystic_tools_agent,
    ],
)
