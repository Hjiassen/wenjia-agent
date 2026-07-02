"""Model configuration helpers for OpenAI-compatible providers."""

from __future__ import annotations

from agents import OpenAIChatCompletionsModel, RunConfig
from agents.models.openai_provider import OpenAIProvider
from agents.run_config import ModelInputData
from openai import AsyncOpenAI

from wenjia_agent.guardrails.input_checks import wenjia_input_guardrail
from wenjia_agent.runtime.config import settings


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


def build_model_provider(openai_client: AsyncOpenAI | None = None) -> OpenAIProvider:
    """Build an OpenAI-compatible provider bound to this project's base URL."""

    return OpenAIProvider(
        openai_client=openai_client or build_openai_client(),
        use_responses=False,
    )


def _memory_input_filter(memory_context: str):
    def filter_input(data) -> ModelInputData:
        instructions = data.model_data.instructions or ""
        if memory_context in instructions:
            next_instructions = instructions
        else:
            next_instructions = f"{instructions}\n\n{memory_context}".strip()
        return ModelInputData(input=data.model_data.input, instructions=next_instructions)

    return filter_input


def build_run_config(
    model_name: str | None = None,
    openai_client: AsyncOpenAI | None = None,
    memory_context: str | None = None,
) -> RunConfig:
    """Build RunConfig without overriding per-Agent models unless requested."""

    return RunConfig(
        model=build_chat_completions_model(model_name, openai_client=openai_client)
        if model_name
        else None,
        model_provider=build_model_provider(openai_client=openai_client),
        input_guardrails=[wenjia_input_guardrail] if settings.input_guardrails_enabled else None,
        call_model_input_filter=_memory_input_filter(memory_context) if memory_context else None,
        tracing_disabled=not settings.openai_sdk_tracing_enabled,
        workflow_name="wenjia-agent",
    )
