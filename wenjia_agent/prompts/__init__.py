"""Prompt template loader."""

from __future__ import annotations

from importlib.resources import files


def load_prompt(name: str) -> str:
    """Load a prompt template from app/prompts."""

    prompt_path = files(__package__).joinpath(name)
    return prompt_path.read_text(encoding="utf-8").strip()
