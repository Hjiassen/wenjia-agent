from agents import OpenAIChatCompletionsModel, RunConfig
from openai import AsyncOpenAI

from wenjia_agent.runtime.models import build_run_config


def test_build_run_config_accepts_slash_model_names():
    client = AsyncOpenAI(api_key="test-key", base_url="https://example.test/v1")
    run_config = build_run_config("deepseek-ai/DeepSeek-V4-Pro", openai_client=client)

    assert isinstance(run_config, RunConfig)
    assert isinstance(run_config.model, OpenAIChatCompletionsModel)
    assert run_config.tracing_disabled is True
