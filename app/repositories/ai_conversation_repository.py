"""Async CRUD repository for AI conversations and messages."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai import AIConversation, AIMessage
from app.services.ai_agent.models import AIScope


def _parse_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    """Convert an optional string UUID to UUID."""
    if value is None or isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


class AIConversationRepository:
    """Repository for persisted AI conversation sessions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_conversation(
        self,
        scope: AIScope,
        *,
        user_id: uuid.UUID | None = None,
        title: str | None = None,
    ) -> AIConversation:
        """Create a new AI conversation scoped to group/greenhouse/zone."""
        conversation = AIConversation(
            group_id=_parse_uuid(scope.group_id),
            greenhouse_id=_parse_uuid(scope.greenhouse_id),
            zone_id=_parse_uuid(scope.zone_id),
            user_id=user_id,
            title=title,
        )
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def get_conversation(self, conversation_id: uuid.UUID) -> AIConversation | None:
        """Fetch a conversation with messages eagerly loaded."""
        stmt = (
            select(AIConversation)
            .where(AIConversation.id == conversation_id)
            .options(selectinload(AIConversation.messages))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_conversations(self) -> list[AIConversation]:
        """List all conversations newest first."""
        stmt = select(AIConversation).order_by(AIConversation.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, conversation_id: uuid.UUID) -> bool:
        """Delete a conversation and its child records."""
        conversation = await self.session.get(AIConversation, conversation_id)
        if conversation is None:
            return False
        await self.session.delete(conversation)
        await self.session.flush()
        return True

    async def add_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        model: str | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
    ) -> AIMessage:
        """Persist one conversation message."""
        message = AIMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            model=model,
            token_input=tokens_in,
            token_output=tokens_out,
        )
        self.session.add(message)
        await self.session.flush()
        return message
