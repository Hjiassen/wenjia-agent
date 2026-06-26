"""Fortune analysis Agent."""

from __future__ import annotations

from agents import Agent

from app.domain.schemas import FortuneReport
from app.prompts import load_prompt
from app.runtime.config import settings
from app.tools.bazi_tools import BAZI_TOOLS


fortune_agent = Agent(
    name="FortuneAgent",
    handoff_description="用于基于确定性八字结果生成命格、事业、财富、感情等分析报告。",
    instructions=load_prompt("fortune_analysis.md"),
    model=settings.openai_analysis_model,
    tools=BAZI_TOOLS,
    output_type=FortuneReport,
)
