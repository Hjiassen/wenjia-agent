"""Username/password authentication with opaque HttpOnly sessions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from apps.web.backend.modules import auth_store
from apps.web.backend.schemas import AuthCredentials, RegisterCredentials
from apps.web.backend.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.auth_session_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )


def optional_current_user(request: Request) -> dict | None:
    token = request.cookies.get(settings.auth_cookie_name)
    return auth_store.resolve_auth_session(token)


def require_current_user(user: dict | None = Depends(optional_current_user)) -> dict:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterCredentials, response: Response) -> dict:
    try:
        auth_store.check_rate_limit(f"register:{payload.username.casefold()}")
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    try:
        user = auth_store.create_user(payload.username, payload.password)
    except auth_store.UsernameTakenError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    _set_session_cookie(response, auth_store.create_auth_session(int(user["id"])))
    auth_store.clear_rate_limit(f"register:{payload.username.casefold()}")
    return {"user": user}


@router.post("/login")
async def login(payload: AuthCredentials, response: Response) -> dict:
    try:
        auth_store.check_rate_limit(f"login:{payload.username.casefold()}")
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    try:
        user = auth_store.authenticate_user(payload.username, payload.password)
    except auth_store.InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    _set_session_cookie(response, auth_store.create_auth_session(int(user["id"])))
    auth_store.clear_rate_limit(f"login:{payload.username.casefold()}")
    return {"user": user}


@router.get("/me")
async def me(user: dict = Depends(require_current_user)) -> dict:
    return {"user": user}


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict:
    token = request.cookies.get(settings.auth_cookie_name)
    auth_store.revoke_auth_session(token)
    response.delete_cookie(
        settings.auth_cookie_name,
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return {"logged_out": True}
