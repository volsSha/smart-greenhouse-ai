"""OpenRouter-backed Pydantic AI agent foundation."""

from __future__ import annotations

import json
import uuid
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.repositories.ai_conversation_repository import AIConversationRepository
from app.repositories.ai_tool_log_repository import AIToolLogRepository
from app.services.ai_agent.models import AIResponse, AIScope
from app.services.ai_agent.prompts import SYSTEM_PROMPT
from app.services.ai_agent.tool_logging import ToolCallLogger


class GreenhouseAIAgent:
    """Service wrapper around Pydantic AI with persistence seams."""

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        agent: Agent[None, AIResponse] | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.conversation_repository = AIConversationRepository(session)
        self.tool_log_repository = AIToolLogRepository(session)
        self.tool_logger = ToolCallLogger(self.tool_log_repository)
        self.agent = agent or self._build_agent(self.settings)

    @staticmethod
    def _build_agent(settings: Settings) -> Agent[None, AIResponse]:
        """Build an OpenAI-compatible Pydantic AI agent for OpenRouter."""
        provider = OpenAIProvider(
            api_key=settings.openrouter.api_key,
            base_url=settings.openrouter.base_url,
        )
        model = OpenAIChatModel(settings.openrouter.model, provider=provider)
        return Agent(model, instructions=SYSTEM_PROMPT, output_type=AIResponse)

    def register_tools(self) -> None:
        """Tool registration seam for U11 read-only tools."""
        return None

    async def chat(
        self,
        message: str,
        conversation_id: uuid.UUID | None = None,
        scope: AIScope | None = None,
    ) -> AIResponse:
        """Run an AI chat turn and persist user/assistant messages."""
        scope = scope or AIScope()
        conversation = None
        if conversation_id is not None:
            conversation = await self.conversation_repository.get_conversation(conversation_id)
        if conversation is None:
            conversation = await self.conversation_repository.create_conversation(
                scope,
                title=message[:80],
            )

        await self.conversation_repository.add_message(
            conversation.id,
            role="user",
            content=message,
        )

        prompt = self._build_scoped_prompt(message, scope)
        result = await self.agent.run(prompt)
        ai_response = result.output

        tokens_in, tokens_out = _extract_usage(result)
        await self.conversation_repository.add_message(
            conversation.id,
            role="assistant",
            content=ai_response.model_dump_json(),
            model=self.settings.openrouter.model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )
        return ai_response

    @staticmethod
    def _build_scoped_prompt(message: str, scope: AIScope) -> str:
        """Attach scoped identifiers without sending unrelated profile data."""
        return (
            "Conversation scope JSON:\n"
            f"{scope.model_dump_json()}\n\n"
            "User message:\n"
            f"{message}"
        )


def _extract_usage(result: Any) -> tuple[int | None, int | None]:
    """Best-effort usage extraction across Pydantic AI model doubles/providers."""
    try:
        usage = result.usage()
    except Exception:
        return None, None

    tokens_in = getattr(usage, "input_tokens", None)
    tokens_out = getattr(usage, "output_tokens", None)
    return tokens_in, tokens_out


def response_to_json(response: AIResponse) -> str:
    """Serialize an AI response for persistence or API output."""
    return json.dumps(response.model_dump(mode="json"), separators=(",", ":"))
