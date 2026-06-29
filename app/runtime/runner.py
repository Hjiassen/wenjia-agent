"""Runner helpers for wenjia-agent."""

from __future__ import annotations

from agents import Runner
from agents.extensions.memory import SQLAlchemySession

from app.agents.main_agent import main_agent
from app.runtime.config import settings
from app.runtime.models import build_run_config


async def run_agent(session_id: str, message: str) -> str:
    """Run the main Agent with SQLAlchemy-backed session memory."""

    session = SQLAlchemySession.from_url(
        session_id=session_id,
        url=settings.session_db_url,
        create_tables=True,
    )
    result = await Runner.run(
        main_agent,
        message,
        session=session,
        run_config=build_run_config(),
    )
    return str(result.final_output)
