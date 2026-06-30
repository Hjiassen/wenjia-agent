"""Agent harness: an explicit control loop around the SDK agent run.

The SDK's ``Runner`` drives the inner reason-act-observe loop. This package adds
an *outer* loop on top of it — Act → Verify → Revise → Finalize — so quality,
safety, and limits are enforced by deterministic code rather than left to the
model's discretion.
"""

from app.harness.loop import ActOutcome, HarnessResult, run_harness
from app.harness.policy import HarnessPolicy, default_policy

__all__ = [
    "ActOutcome",
    "HarnessResult",
    "run_harness",
    "HarnessPolicy",
    "default_policy",
]
