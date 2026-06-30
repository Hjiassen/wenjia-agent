"""Runner helpers for wenjia-agent."""

from __future__ import annotations

from agents import Runner
from agents.exceptions import MaxTurnsExceeded
from agents.extensions.memory import SQLAlchemySession

from app.agents.main_agent import main_agent
from app.guardrails.output_checks import run_output_checks
from app.harness.loop import ActOutcome, run_harness
from app.harness.policy import default_policy
from app.runtime import profile_store
from app.runtime.config import settings
from app.runtime.models import build_run_config
from app.runtime.output_format import format_final_output
from app.runtime.run_context import WenjiaRunContext

_MAX_TURNS_MESSAGE = "推演步骤过多已中止，请补充更完整的信息或简化问题后重试。"


async def run_agent(session_id: str, message: str) -> str:
    """Run the main Agent through the harness loop with session memory."""

    session = SQLAlchemySession.from_url(
        session_id=session_id,
        url=settings.session_db_url,
        create_tables=True,
    )
    context = WenjiaRunContext(session_id=session_id)
    policy = default_policy()

    async def act(correction: str | None) -> ActOutcome:
        result = await Runner.run(
            main_agent,
            correction or message,
            session=session,
            context=context,
            max_turns=policy.max_turns,
            run_config=build_run_config(),
        )
        return ActOutcome(result.final_output, format_final_output(result.final_output))

    def verify(outcome: ActOutcome):
        return run_output_checks(
            outcome.rendered_text,
            outcome.final_output,
            profile_store.list_profiles(session_id),
        )

    try:
        result = await run_harness(act, verify, policy)
    except MaxTurnsExceeded:
        return _MAX_TURNS_MESSAGE
    return result.rendered_text
