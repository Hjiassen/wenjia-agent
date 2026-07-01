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


def default_policy() -> HarnessPolicy:
    """Build the policy from runtime settings."""

    return HarnessPolicy(
        max_turns=settings.harness_max_turns,
        max_revisions=settings.harness_max_revisions,
        revise_enabled=settings.harness_revise_enabled,
    )
