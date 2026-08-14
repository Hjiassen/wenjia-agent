"""Pending profile-candidate endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from apps.web.backend.api.auth import require_current_user
from apps.web.backend.modules import profile_candidate_store, profile_store
from apps.web.backend.schemas import (
    ProfileCandidateConvertPayload,
    ProfileCandidatePayload,
    ProfileCandidateUpdate,
)

router = APIRouter()


@router.get("/profile-candidates")
async def list_profile_candidates(
    candidate_status: str = Query(default="pending", alias="status", pattern="^(pending|dismissed|converted|all)$"),
    user: dict = Depends(require_current_user),
) -> dict:
    return {
        "candidates": profile_candidate_store.list_candidates(
            int(user["id"]), status=candidate_status
        )
    }


@router.post("/profile-candidates", status_code=status.HTTP_201_CREATED)
async def create_profile_candidate(
    payload: ProfileCandidatePayload,
    user: dict = Depends(require_current_user),
) -> dict:
    candidate = profile_candidate_store.create_candidate(
        int(user["id"]), payload.model_dump()
    )
    return {"candidate": candidate}


@router.put("/profile-candidates/{candidate_id:int}")
async def update_profile_candidate(
    candidate_id: int,
    payload: ProfileCandidateUpdate,
    user: dict = Depends(require_current_user),
) -> dict:
    try:
        candidate = profile_candidate_store.update_candidate(
            int(user["id"]), candidate_id, payload.model_dump()
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"candidate": candidate}


@router.post("/profile-candidates/{candidate_id:int}/dismiss")
async def dismiss_profile_candidate(
    candidate_id: int,
    user: dict = Depends(require_current_user),
) -> dict:
    try:
        candidate = profile_candidate_store.set_status(
            int(user["id"]), candidate_id, "dismissed"
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"candidate": candidate}


@router.post("/profile-candidates/{candidate_id:int}/convert", status_code=status.HTTP_201_CREATED)
async def convert_profile_candidate(
    candidate_id: int,
    payload: ProfileCandidateConvertPayload,
    user: dict = Depends(require_current_user),
) -> dict:
    user_id = int(user["id"])
    try:
        candidate, profile = profile_candidate_store.convert_candidate(
            user_id, candidate_id, payload.model_dump()
        )
    except profile_store.ProfileConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"candidate": candidate, "profile": profile}
