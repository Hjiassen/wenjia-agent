"""Runner helpers for wenjia-agent."""

from __future__ import annotations

from agents import Runner
from agents.exceptions import MaxTurnsExceeded
from agents.extensions.memory import SQLAlchemySession

from app.agents.main_agent import main_agent
from app.runtime.config import settings
from app.runtime.models import build_run_config
from app.runtime.run_context import WenjiaRunContext

MAX_TURNS = 16
_MAX_TURNS_MESSAGE = "推演步骤过多已中止，请补充更完整的信息或简化问题后重试。"


async def run_agent(session_id: str, message: str) -> str:
    """Run the main Agent with SQLAlchemy-backed session memory."""

    session = SQLAlchemySession.from_url(
        session_id=session_id,
        url=settings.session_db_url,
        create_tables=True,
    )
    try:
        result = await Runner.run(
            main_agent,
            message,
            session=session,
            context=WenjiaRunContext(session_id=session_id),
            max_turns=MAX_TURNS,
            run_config=build_run_config(),
        )
    except MaxTurnsExceeded:
        return _MAX_TURNS_MESSAGE
    return str(result.final_output)
