"""OpenAI Agents SDK CLI demo.

Requires OPENAI_API_KEY in the environment.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.runtime.runner import run_agent


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


async def main() -> None:
    _configure_stdout()
    session_id = f"wenjia:{uuid.uuid4()}"
    print("问甲 Agent CLI，输入 exit 退出。")
    while True:
        message = input("> ").strip()
        if message.lower() in {"exit", "quit"}:
            break
        output = await run_agent(session_id, message)
        print(output)


if __name__ == "__main__":
    asyncio.run(main())
