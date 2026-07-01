"""Chat endpoints: non-streaming JSON and streaming SSE."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from wenjia_agent.runtime.runner import run_agent
from wenjia_agent.runtime.stream_runner import stream_agent_events

from ..schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    """Run one Agent turn and return the final output."""

    session_id = payload.session_id or f"web:{uuid.uuid4()}"
    try:
        output = await run_agent(session_id=session_id, message=payload.message.strip())
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - web transport boundary.
        raise HTTPException(status_code=502, detail=f"Agent request failed: {exc}") from exc

    return ChatResponse(session_id=session_id, output=output)


@router.post("/chat/stream")
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
