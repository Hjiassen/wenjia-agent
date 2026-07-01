import asyncio

from wenjia_agent.guardrails.output_checks import Issue
from wenjia_agent.harness.loop import ActOutcome, run_harness
from wenjia_agent.harness.policy import HarnessPolicy


def _run(act, verify, policy, on_event=None):
    return asyncio.run(run_harness(act, verify, policy, on_event=on_event))


def test_clean_first_attempt_no_revision():
    async def act(_correction):
        return ActOutcome("ok", "干净的回答")

    result = _run(act, lambda _o: [], HarnessPolicy())
    assert result.attempts == 0
    assert result.rendered_text == "干净的回答"


def test_revises_once_then_passes():
    calls = {"n": 0}

    async def act(correction):
        calls["n"] += 1
        # First attempt is bad, revision (correction is not None) is clean.
        return ActOutcome("x", "已修正" if correction else "有问题")

    def verify(outcome):
        return [] if outcome.rendered_text == "已修正" else [Issue("bad", "有问题", "error")]

    events = []

    async def on_event(ev):
        events.append(ev["type"])

    result = _run(act, verify, HarnessPolicy(max_revisions=1), on_event=on_event)
    assert calls["n"] == 2
    assert result.attempts == 1
    assert result.rendered_text == "已修正"
    assert "revise" in events
    assert "verify" in events


def test_respects_max_revisions():
    calls = {"n": 0}

    async def act(_correction):
        calls["n"] += 1
        return ActOutcome("x", "始终有问题")

    def verify(_outcome):
        return [Issue("bad", "有问题", "error")]

    result = _run(act, verify, HarnessPolicy(max_revisions=2))
    assert calls["n"] == 3  # first attempt + 2 revisions
    assert result.attempts == 2


def test_revise_disabled_never_retries():
    calls = {"n": 0}

    async def act(_correction):
        calls["n"] += 1
        return ActOutcome("x", "有问题")

    def verify(_outcome):
        return [Issue("bad", "有问题", "error")]

    result = _run(act, verify, HarnessPolicy(revise_enabled=False, max_revisions=3))
    assert calls["n"] == 1
    assert result.attempts == 0


def test_warn_issue_does_not_trigger_revision_but_remediates_boundary():
    async def act(_correction):
        return ActOutcome("x", "报告正文")

    def verify(_outcome):
        return [Issue("missing_boundary", "缺少边界提醒", "warn")]

    result = _run(act, verify, HarnessPolicy())
    assert result.attempts == 0  # warn does not trigger revision
    assert "仅作文化娱乐与个人参考" in result.rendered_text  # boundary remediated
