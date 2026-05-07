"""REST endpoints for scoped AI chat, conversations, and tool logs."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.repositories.ai_conversation_repository import AIConversationRepository
from app.repositories.ai_tool_log_repository import AIToolLogRepository
from app.services.ai_agent.agent import GreenhouseAIAgent
from app.services.ai_agent.models import AIResponse, AIScope

router = APIRouter(prefix="/api/ai", tags=["ai"])


class AIChatRequest(BaseModel):
    """Request body for a scoped AI chat turn."""

    message: str
    conversation_id: UUID | None = None
    scope: AIScope = AIScope()


class AIConversationSummary(BaseModel):
    """Conversation list item."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_id: UUID | None
    greenhouse_id: UUID | None
    zone_id: UUID | None
    title: str | None


class AIMessageResponse(BaseModel):
    """Persisted AI message response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    model: str | None
    token_input: int | None
    token_output: int | None


class AIConversationDetail(AIConversationSummary):
    """Conversation with messages."""

    messages: list[AIMessageResponse]


class AIToolCallResponse(BaseModel):
    """Persisted tool-call response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any] | None
    status: str
    error: str | None


@router.post("/chat", response_model=AIResponse)
async def chat(
    body: AIChatRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AIResponse:
    """Send one scoped chat message and return a structured AI response."""
    service = GreenhouseAIAgent(session)
    response = await service.chat(
        message=body.message,
        conversation_id=body.conversation_id,
        scope=body.scope,
    )
    await session.commit()
    return response


@router.get("/conversations", response_model=list[AIConversationSummary])
async def list_conversations(
    session: AsyncSession = Depends(get_db_session),
) -> list[AIConversationSummary]:
    """List AI conversations."""
    repo = AIConversationRepository(session)
    conversations = await repo.list_conversations()
    return [AIConversationSummary.model_validate(conv) for conv in conversations]


@router.get("/conversations/{conversation_id}", response_model=AIConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AIConversationDetail:
    """Get one conversation with persisted messages."""
    repo = AIConversationRepository(session)
    conversation = await repo.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return AIConversationDetail.model_validate(conversation)


@router.get("/tool-calls/{conversation_id}", response_model=list[AIToolCallResponse])
async def get_tool_calls(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[AIToolCallResponse]:
    """Get tool-call logs for a conversation."""
    repo = AIToolLogRepository(session)
    tool_calls = await repo.get_tool_calls(conversation_id)
    return [AIToolCallResponse.model_validate(call) for call in tool_calls]


def parse_assistant_content(content: str) -> dict[str, Any]:
    """Parse persisted assistant JSON content for UI clients when needed."""
    return json.loads(content)
