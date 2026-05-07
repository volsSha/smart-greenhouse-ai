"""Async CRUD repository for AI tool-call logs."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AIToolCall


class AIToolLogRepository:
    """Repository for persisted AI tool invocations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log_tool_call(
        self,
        conversation_id: uuid.UUID,
        tool_name: str,
        arguments: dict[str, Any],
        result: dict[str, Any] | None,
        status: str,
        error: str | None = None,
    ) -> AIToolCall:
        """Persist a sanitized tool-call record."""
        tool_call = AIToolCall(
            conversation_id=conversation_id,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            status=status,
            error=error,
        )
        self.session.add(tool_call)
        await self.session.flush()
        return tool_call

    async def get_tool_calls(self, conversation_id: uuid.UUID) -> list[AIToolCall]:
        """Return tool calls for a conversation in creation order."""
        stmt = (
            select(AIToolCall)
            .where(AIToolCall.conversation_id == conversation_id)
            .order_by(AIToolCall.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
