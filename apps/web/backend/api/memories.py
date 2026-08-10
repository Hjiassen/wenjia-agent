"""Long-term memory management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from apps.web.backend.api.auth import require_current_user
from apps.web.backend.schemas import MemoryPayload
from wenjia_agent.runtime import memory_store

router = APIRouter()


def _reject_legacy_identity(request: Request) -> None:
    if "client_id" in request.query_params:
        raise HTTPException(status_code=422, detail="client_id is no longer supported")


@router.get("/memories")
async def list_memories(
    request: Request,
    query: str | None = Query(default=None, max_length=8000),
    user: dict = Depends(require_current_user),
) -> dict:
    """Return memories owned by the authenticated account."""

    _reject_legacy_identity(request)
    owner_id = f"user:{int(user['id'])}"
    memories = memory_store.list_memories(owner_id, query=query)

    return {
        "user_id": owner_id,
        "memories": memories,
    }


@router.post("/memories", status_code=status.HTTP_201_CREATED)
async def create_memory(
    payload: MemoryPayload,
    user: dict = Depends(require_current_user),
) -> dict:
    try:
        memory = memory_store.upsert_memory(
            f"user:{int(user['id'])}",
            kind=payload.kind,
            key=payload.key,
            title=payload.title,
            content=payload.content,
            payload=payload.payload,
            source_session_id=payload.source_session_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"memory": memory}


@router.put("/memories/{memory_id}")
async def update_memory(
    memory_id: int,
    payload: MemoryPayload,
    user: dict = Depends(require_current_user),
) -> dict:
    try:
        memory = memory_store.update_memory(
            f"user:{int(user['id'])}",
            memory_id,
            kind=payload.kind,
            key=payload.key,
            title=payload.title,
            content=payload.content,
            payload=payload.payload,
            source_session_id=payload.source_session_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"memory": memory}


@router.delete("/memories/{memory_id}")
async def delete_memory(
    memory_id: int,
    request: Request,
    user: dict = Depends(require_current_user),
) -> dict:
    """Delete one long-term memory item owned by the account."""

    _reject_legacy_identity(request)
    owner_id = f"user:{int(user['id'])}"
    deleted = memory_store.delete_memory(owner_id, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="memory not found")
    return {
        "user_id": owner_id,
        "memory_id": memory_id,
        "deleted": True,
    }
