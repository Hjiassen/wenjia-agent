"""Application lifespan: initialize persistence on startup."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from wenjia_agent.runtime import profile_store


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Ensure the person-profile table exists before the first chart is saved."""

    profile_store.init_db()
    yield
