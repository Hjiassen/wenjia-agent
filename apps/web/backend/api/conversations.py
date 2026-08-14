"""Authenticated conversation query and deletion endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from apps.web.backend.api.auth import require_current_user
from apps.web.backend.modules import chat_jobs
from apps.web.backend.modules import conversation_store

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
async def list_conversations(user: dict = Depends(require_current_user)) -> dict:
    user_id = int(user["id"])
    conversations = conversation_store.list_conversations(user_id)
    for conversation in conversations:
        conversation["running"] = chat_jobs.is_running(user_id, conversation["id"])
    return {"conversations": conversations}


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str, user: dict = Depends(require_current_user)) -> dict:
    conversation = conversation_store.get_conversation(int(user["id"]), conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")
    conversation["running"] = chat_jobs.is_running(int(user["id"]), conversation_id)
    return {"conversation": conversation}


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, user: dict = Depends(require_current_user)) -> dict:
    if not conversation_store.delete_conversation(int(user["id"]), conversation_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")
    return {"deleted": True}


@router.delete("")
async def clear_conversations(user: dict = Depends(require_current_user)) -> dict:
    return {"deleted": conversation_store.clear_conversations(int(user["id"]))}
