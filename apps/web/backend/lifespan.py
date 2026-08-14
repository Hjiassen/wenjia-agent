"""Application lifespan: initialize persistence on startup."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.web.backend.modules import migrations
from apps.web.backend.modules import chat_jobs


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Ensure the person-profile table exists before the first chart is saved."""

    migrations.run_migrations()
    try:
        yield
    finally:
        await chat_jobs.shutdown()
