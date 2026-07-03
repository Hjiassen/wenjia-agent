"""Long-term memory management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from wenjia_agent.runtime import memory_store

router = APIRouter()


@router.get("/memories")
async def list_memories(
    client_id: str = Query(..., min_length=1, max_length=128),
    query: str | None = Query(default=None, max_length=8000),
) -> dict:
    """Return long-term memories owned by the browser client id."""

    return {
        "client_id": client_id,
        "memories": memory_store.list_memories(client_id, query=query),
    }


@router.delete("/memories/{memory_id}")
async def delete_memory(
    memory_id: int,
    client_id: str = Query(..., min_length=1, max_length=128),
) -> dict:
    """Delete one long-term memory item owned by the browser client id."""

    deleted = memory_store.delete_memory(client_id, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="memory not found")
    return {"client_id": client_id, "memory_id": memory_id, "deleted": True}
