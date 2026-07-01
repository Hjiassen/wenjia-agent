"""Health check endpoint used by the browser demo."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, bool]:
    """Report backend availability."""

    return {"ok": True}
