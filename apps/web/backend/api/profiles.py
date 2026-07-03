"""Person-profile (人物档案) lookup endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wenjia_agent.core.city_data import get_cities, get_provinces
from wenjia_agent.runtime import profile_store
from apps.web.backend.schemas import ProfilePayload

router = APIRouter()


@router.get("/profiles/meta/cities")
async def get_profile_city_options() -> dict:
    """Return two-level province/city options for profile forms."""

    return {
        "options": [
            {
                "label": province,
                "value": province,
                "children": [
                    {"label": city, "value": city}
                    for city in get_cities(province)
                ],
            }
            for province in get_provinces()
        ]
    }


@router.get("/profiles/{session_id}")
async def get_profiles(session_id: str) -> dict:
    """Return person profiles saved for a conversation."""

    return {"session_id": session_id, "profiles": profile_store.list_profiles(session_id)}


@router.post("/profiles/{session_id}")
async def create_profile(session_id: str, payload: ProfilePayload) -> dict:
    """Create a person profile for a conversation."""

    try:
        profile = profile_store.upsert_manual_profile(
            session_id,
            payload.model_dump(exclude={"client_id"}),
            user_id=payload.client_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"session_id": session_id, "profile": profile}


@router.put("/profiles/{session_id}/{profile_id}")
async def update_profile(session_id: str, profile_id: int, payload: ProfilePayload) -> dict:
    """Update a person profile owned by a conversation."""

    try:
        profile = profile_store.upsert_manual_profile(
            session_id,
            payload.model_dump(exclude={"client_id"}),
            profile_id=profile_id,
            user_id=payload.client_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"session_id": session_id, "profile": profile}
