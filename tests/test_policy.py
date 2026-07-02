from wenjia_agent.harness.policy import default_policy
from wenjia_agent.runtime.config import settings


def test_default_policy_reads_timeout_and_fallback(monkeypatch):
    monkeypatch.setattr(settings, "harness_model_timeout_seconds", 12.5)
    monkeypatch.setattr(settings, "openai_fallback_model", "fallback-model")

    policy = default_policy()

    assert policy.model_timeout_seconds == 12.5
    assert policy.fallback_model == "fallback-model"


def test_default_policy_treats_blank_fallback_as_disabled(monkeypatch):
    monkeypatch.setattr(settings, "openai_fallback_model", "  ")

    assert default_policy().fallback_model is None
