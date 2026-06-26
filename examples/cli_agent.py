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


async def main() -> None:
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
