"""FastAPI web demo for wenjia-agent."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.runtime.runner import run_agent
from app.runtime.stream_runner import stream_agent_events

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="wenjia-agent web demo",
    description="A lightweight web chat demo for wenjia-agent.",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    """Request payload for one chat turn."""

    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, max_length=128)


class ChatResponse(BaseModel):
    """Response payload for one chat turn."""

    session_id: str
    output: str


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    """Serve the demo UI."""

    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, bool]:
    """Health check endpoint used by the browser demo."""

    return {"ok": True}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    """Run one Agent turn and return the final output."""

    session_id = payload.session_id or f"web:{uuid.uuid4()}"
    try:
        output = await run_agent(session_id=session_id, message=payload.message.strip())
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - web demo boundary.
        raise HTTPException(status_code=502, detail=f"Agent request failed: {exc}") from exc

    return ChatResponse(session_id=session_id, output=output)


@app.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest) -> StreamingResponse:
    """Run one Agent turn and stream visualization events via SSE."""

    session_id = payload.session_id or f"web:{uuid.uuid4()}"

    async def event_generator():
        async for event in stream_agent_events(
            session_id=session_id,
            message=payload.message.strip(),
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
