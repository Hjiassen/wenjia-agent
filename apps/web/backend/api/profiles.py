"""Person-profile (人物档案) lookup endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from wenjia_agent.core.city_data import get_cities, get_provinces
from apps.web.backend.schemas import ProfilePayload
from apps.web.backend.modules import profile_store as account_profile_store
from apps.web.backend.api.auth import require_current_user

router = APIRouter()


@router.get("/profiles/meta/cities")
async def get_profile_city_options(_user: dict = Depends(require_current_user)) -> dict:
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


def _account_data(payload: ProfilePayload) -> dict:
    return payload.model_dump()


@router.get("/profiles")
async def list_account_profiles(user: dict = Depends(require_current_user)) -> dict:
    return {"profiles": account_profile_store.list_profiles(int(user["id"]))}


@router.get("/profiles/deleted")
async def list_deleted_account_profiles(user: dict = Depends(require_current_user)) -> dict:
    return {
        "profiles": account_profile_store.list_profiles(
            int(user["id"]), only_deleted=True
        )[::-1]
    }


@router.post("/profiles", status_code=status.HTTP_201_CREATED)
async def create_account_profile(
    payload: ProfilePayload,
    user: dict = Depends(require_current_user),
) -> dict:
    try:
        profile = account_profile_store.create_profile(int(user["id"]), _account_data(payload))
    except account_profile_store.ProfileConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"profile": profile}
@router.get("/profiles/{profile_id:int}")
async def get_account_profile(profile_id: int, user: dict = Depends(require_current_user)) -> dict:
    try:
        profile = account_profile_store.get_profile(int(user["id"]), profile_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"profile": profile}


@router.put("/profiles/{profile_id:int}")
async def update_account_profile(
    profile_id: int,
    payload: ProfilePayload,
    user: dict = Depends(require_current_user),
) -> dict:
    try:
        profile = account_profile_store.update_profile(
            int(user["id"]), profile_id, _account_data(payload)
        )
    except account_profile_store.ProfileConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"profile": profile}


@router.delete("/profiles/{profile_id:int}")
async def delete_account_profile(profile_id: int, user: dict = Depends(require_current_user)) -> dict:
    try:
        profile = account_profile_store.soft_delete_profile(int(user["id"]), profile_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"profile": profile, "deleted": True}


@router.post("/profiles/{profile_id:int}/restore")
async def restore_account_profile(profile_id: int, user: dict = Depends(require_current_user)) -> dict:
    try:
        profile = account_profile_store.restore_profile(int(user["id"]), profile_id)
    except account_profile_store.ProfileConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"profile": profile}
