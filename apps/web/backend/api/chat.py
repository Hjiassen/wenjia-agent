"""Chat endpoints: non-streaming JSON and streaming SSE."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from wenjia_agent.runtime.runner import run_agent
from wenjia_agent.runtime.stream_runner import stream_agent_events
from wenjia_agent.runtime.suggestions import generate_suggestions
from apps.web.backend.api.auth import require_current_user
from apps.web.backend.modules import profile_store as account_profile_store

from ..schemas import (
    ChatRequest,
    ChatResponse,
    SuggestionRequest,
    SuggestionResponse,
)

router = APIRouter()


def _account_run_options(payload: ChatRequest, user: dict) -> tuple[str, dict]:
    """Resolve authenticated ownership and explicitly selected active profiles."""

    user_id = int(user["id"])
    try:
        profiles = account_profile_store.get_profiles_by_ids(user_id, payload.profile_ids)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    def profile_writer(relationship_type: str, bazi: dict, context: dict) -> dict:
        return account_profile_store.save_computed_profile(
            user_id,
            relationship_type,
            bazi,
            context,
            source_session_id=payload.session_id,
        )

    return f"user:{user_id}", {"profile_context": profiles, "profile_writer": profile_writer}


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    user: dict = Depends(require_current_user),
) -> ChatResponse:
    """Run one Agent turn and return the final output."""

    session_id = payload.session_id or f"web:{uuid.uuid4()}"
    effective_user_id, run_options = _account_run_options(payload, user)
    try:
        output = await run_agent(
            session_id=session_id,
            message=payload.message.strip(),
            user_id=effective_user_id,
            **run_options,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - web transport boundary.
        raise HTTPException(status_code=502, detail=f"Agent request failed: {exc}") from exc

    return ChatResponse(session_id=session_id, output=output)


@router.post("/chat/suggestions", response_model=SuggestionResponse)
async def chat_suggestions(
    payload: SuggestionRequest,
    _user: dict = Depends(require_current_user),
) -> SuggestionResponse:
    """Generate lightweight follow-up question suggestions for a finished turn."""

    suggestions = await generate_suggestions(
        session_id=payload.session_id,
        user_message=payload.user_message,
        assistant_message=payload.assistant_message,
    )
    return SuggestionResponse(
        suggestions=[item.prompt for item in suggestions]
    )


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    user: dict = Depends(require_current_user),
) -> StreamingResponse:
    """Run one Agent turn and stream visualization events via SSE."""

    session_id = payload.session_id or f"web:{uuid.uuid4()}"
    effective_user_id, run_options = _account_run_options(payload, user)

    async def event_generator():
        async for event in stream_agent_events(
            session_id=session_id,
            message=payload.message.strip(),
            user_id=effective_user_id,
            **run_options,
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
