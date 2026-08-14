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
from apps.web.backend.modules import conversation_store
from apps.web.backend.modules.profile_candidate_detector import detect_profile_candidates

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
    if not conversation_store.can_access(int(user["id"]), session_id):
        raise HTTPException(status_code=404, detail="conversation not found")
    effective_user_id, run_options = _account_run_options(payload, user)
    conversation_store.append_message(
        int(user["id"]),
        session_id,
        "user",
        payload.message.strip(),
        payload={
            "profileContext": [
                {
                    "id": profile["id"],
                    "name": profile["name"],
                    "relationship_type": profile["relationship_type"],
                }
                for profile in run_options["profile_context"]
            ]
        },
    )
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

    candidate_suggestions = detect_profile_candidates(payload.message, session_id)
    conversation_store.append_message(
        int(user["id"]),
        session_id,
        "assistant",
        output,
        payload={"flow": [], "candidateSuggestions": candidate_suggestions},
    )

    return ChatResponse(session_id=session_id, output=output)


@router.post("/chat/suggestions", response_model=SuggestionResponse)
async def chat_suggestions(
    payload: SuggestionRequest,
    user: dict = Depends(require_current_user),
) -> SuggestionResponse:
    """Generate lightweight follow-up question suggestions for a finished turn."""

    if payload.session_id and conversation_store.get_conversation(int(user["id"]), payload.session_id) is None:
        raise HTTPException(status_code=404, detail="conversation not found")

    suggestions = await generate_suggestions(
        session_id=payload.session_id,
        user_message=payload.user_message,
        assistant_message=payload.assistant_message,
    )
    suggestion_values = [item.prompt for item in suggestions]
    conversation_store.update_latest_assistant_suggestions(
        int(user["id"]),
        payload.session_id or "",
        payload.assistant_message,
        [{"prompt": item} for item in suggestion_values],
    )
    return SuggestionResponse(suggestions=suggestion_values)


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    user: dict = Depends(require_current_user),
) -> StreamingResponse:
    """Run one Agent turn and stream visualization events via SSE."""

    session_id = payload.session_id or f"web:{uuid.uuid4()}"
    if not conversation_store.can_access(int(user["id"]), session_id):
        raise HTTPException(status_code=404, detail="conversation not found")
    effective_user_id, run_options = _account_run_options(payload, user)
    conversation_store.append_message(
        int(user["id"]),
        session_id,
        "user",
        payload.message.strip(),
        payload={
            "profileContext": [
                {
                    "id": profile["id"],
                    "name": profile["name"],
                    "relationship_type": profile["relationship_type"],
                }
                for profile in run_options["profile_context"]
            ]
        },
    )

    async def event_generator():
        events: list[dict] = []
        assistant_body = ""
        assistant_type = ""
        candidate_suggestions = detect_profile_candidates(payload.message, session_id)
        try:
            async for event in stream_agent_events(
                session_id=session_id,
                message=payload.message.strip(),
                user_id=effective_user_id,
                **run_options,
            ):
                events.append(event)
                if event.get("type") == "answer_delta":
                    assistant_body += event.get("delta", "")
                elif event.get("type") == "done":
                    assistant_body = event.get("content") or assistant_body
                    event["candidate_suggestions"] = candidate_suggestions
                elif event.get("type") == "error":
                    assistant_type = "error"
                    assistant_body = event.get("message") or assistant_body or "请求失败。"
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        finally:
            flow = [event for event in events if event.get("type") not in {"answer_delta", "answer_reset"}]
            if not assistant_body:
                assistant_body = "（生成未完成）"
                assistant_type = "error"
            conversation_store.append_message(
                int(user["id"]),
                session_id,
                "assistant",
                assistant_body,
                payload={
                    "flow": flow,
                    "type": assistant_type,
                    "candidateSuggestions": candidate_suggestions
                    if not assistant_type
                    else [],
                },
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
