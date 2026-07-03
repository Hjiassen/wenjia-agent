"""Application factory: wire routers, CORS, and lifespan into a FastAPI app."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat, health, memories, profiles
from .lifespan import lifespan
from .settings import settings


def create_app() -> FastAPI:
    """Build the API-only FastAPI backend for the wenjia-agent web app."""

    app = FastAPI(
        title="wenjia-agent web backend",
        description="API-only backend for the wenjia-agent web app.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(chat.router, prefix="/api")
    app.include_router(profiles.router, prefix="/api")
    app.include_router(memories.router, prefix="/api")

    return app
