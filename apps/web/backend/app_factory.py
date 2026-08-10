"""Application factory: wire routers, CORS, and lifespan into a FastAPI app."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .api import auth, chat, health, memories, profiles
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

    @app.middleware("http")
    async def csrf_guard(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.cookies.get(settings.auth_cookie_name):
            origin = request.headers.get("origin")
            if origin and origin not in settings.cors_origins:
                return JSONResponse({"detail": "invalid request origin"}, status_code=403)
        return await call_next(request)

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(profiles.router, prefix="/api")
    app.include_router(memories.router, prefix="/api")

    return app
