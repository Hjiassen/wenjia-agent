"""Person-profile (人物档案) lookup endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wenjia_agent.runtime import profile_store
from apps.web.backend.schemas import ProfilePayload

router = APIRouter()


@router.get("/profiles/{session_id}")
async def get_profiles(session_id: str) -> dict:
    """Return person profiles saved for a conversation."""

    return {"session_id": session_id, "profiles": profile_store.list_profiles(session_id)}


@router.post("/profiles/{session_id}")
async def create_profile(session_id: str, payload: ProfilePayload) -> dict:
    """Create a person profile for a conversation."""

    try:
        profile = profile_store.upsert_manual_profile(session_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"session_id": session_id, "profile": profile}


@router.put("/profiles/{session_id}/{profile_id}")
async def update_profile(session_id: str, profile_id: int, payload: ProfilePayload) -> dict:
    """Update a person profile owned by a conversation."""

    try:
        profile = profile_store.upsert_manual_profile(
            session_id,
            payload.model_dump(),
            profile_id=profile_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"session_id": session_id, "profile": profile}
