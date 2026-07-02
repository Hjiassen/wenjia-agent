"""Harness execution policy (limits and toggles)."""

from __future__ import annotations

from dataclasses import dataclass

from wenjia_agent.runtime.config import settings


@dataclass(frozen=True)
class HarnessPolicy:
    """Bounds for one harnessed run."""

    max_turns: int = 16
    max_revisions: int = 1
    revise_enabled: bool = True
    model_timeout_seconds: float = 90.0
    fallback_model: str | None = None


def default_policy() -> HarnessPolicy:
    """Build the policy from runtime settings."""

    return HarnessPolicy(
        max_turns=settings.harness_max_turns,
        max_revisions=settings.harness_max_revisions,
        revise_enabled=settings.harness_revise_enabled,
        model_timeout_seconds=settings.harness_model_timeout_seconds,
        fallback_model=settings.openai_fallback_model.strip() or None,
    )
