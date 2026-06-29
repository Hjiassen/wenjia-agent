"""Model configuration helpers for OpenAI-compatible providers."""

from __future__ import annotations

from agents import OpenAIChatCompletionsModel, RunConfig
from openai import AsyncOpenAI

from app.runtime.config import settings


def build_openai_client(
    api_key: str | None = None,
    base_url: str | None = None,
) -> AsyncOpenAI:
    """Build an AsyncOpenAI client from runtime settings."""

    effective_api_key = api_key if api_key is not None else settings.openai_api_key
    if not effective_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to run wenjia-agent.")

    return AsyncOpenAI(
        api_key=effective_api_key,
        base_url=base_url or settings.openai_base_url,
    )


def build_chat_completions_model(
    model_name: str,
    openai_client: AsyncOpenAI | None = None,
) -> OpenAIChatCompletionsModel:
    """Build a Chat Completions model without interpreting slashes as provider prefixes."""

    return OpenAIChatCompletionsModel(
        model=model_name,
        openai_client=openai_client or build_openai_client(),
    )


def build_run_config(
    model_name: str | None = None,
    openai_client: AsyncOpenAI | None = None,
) -> RunConfig:
    """Build the RunConfig used by CLI and embedded runtime calls."""

    return RunConfig(
        model=build_chat_completions_model(
            model_name or settings.openai_agent_model,
            openai_client=openai_client,
        ),
        tracing_disabled=True,
        workflow_name="wenjia-agent",
    )
