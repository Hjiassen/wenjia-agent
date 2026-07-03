"""Test environment setup."""

from __future__ import annotations

import os

if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "test-key"

os.environ.setdefault("OPENAI_AGENTS_DISABLE_TRACING", "true")
