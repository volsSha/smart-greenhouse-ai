"""OpenRouter-backed Pydantic AI agent foundation."""

from __future__ import annotations

import json
import uuid
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.repositories.ai_conversation_repository import AIConversationRepository
from app.repositories.ai_tool_log_repository import AIToolLogRepository
from app.repositories.alert_repository import AlertRepository
from app.repositories.command_repository import CommandRepository
from app.repositories.device_repository import ActuatorRepository, SensorRepository
from app.repositories.greenhouse_repository import GreenhouseRepository
from app.repositories.group_repository import GroupRepository
from app.repositories.plant_batch_repository import (
    PlantBatchRepository,
    PlantProfileRepository,
)
from app.repositories.telemetry_repository import TelemetryRepository
from app.repositories.zone_repository import ZoneRepository
from app.services.ai_agent.models import AIResponse, AIScope
from app.services.ai_agent.prompts import SYSTEM_PROMPT
from app.services.ai_agent.tool_logging import ToolCallLogger
from app.services.ai_agent.tools import ALL_TOOLS
from app.services.ai_agent.tools.deps import ToolDeps


class AIConfigurationError(Exception):
    """Raised when the AI provider is not configured."""


class GreenhouseAIAgent:
    """Service wrapper around Pydantic AI with persistence seams."""

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        agent: Agent[ToolDeps, AIResponse] | None = None,
        telemetry_repository: TelemetryRepository | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.telemetry_repository = telemetry_repository
        self.conversation_repository = AIConversationRepository(session)
        self.tool_log_repository = AIToolLogRepository(session)
        self.tool_logger = ToolCallLogger(self.tool_log_repository)
        self.agent = agent or self._build_agent(self.settings)
        if agent is None:
            self.register_tools()

    def _build_deps(self) -> ToolDeps:
        """Build the dependency container for tool functions."""
        return ToolDeps(
            group_repo=GroupRepository(self.session),
            greenhouse_repo=GreenhouseRepository(self.session),
            zone_repo=ZoneRepository(self.session),
            alert_repo=AlertRepository(self.session),
            command_repo=CommandRepository(self.session),
            plant_batch_repo=PlantBatchRepository(self.session),
            plant_profile_repo=PlantProfileRepository(self.session),
            telemetry_repo=self.telemetry_repository or TelemetryRepository(None),
            sensor_repo=SensorRepository(self.session),
            actuator_repo=ActuatorRepository(self.session),
            tool_logger=self.tool_logger,
        )

    @staticmethod
    def _build_agent(settings: Settings) -> Agent[ToolDeps, AIResponse]:
        """Build an OpenAI-compatible Pydantic AI agent for OpenRouter."""
        if not settings.openrouter.api_key.strip():
            raise AIConfigurationError("OpenRouter API key is not configured")
        provider = OpenAIProvider(
            api_key=settings.openrouter.api_key,
            base_url=settings.openrouter.base_url,
        )
        model = OpenAIChatModel(settings.openrouter.model, provider=provider)
        return Agent(
            model,
            instructions=SYSTEM_PROMPT,
            output_type=AIResponse,
            deps_type=ToolDeps,
        )

    def register_tools(self) -> None:
        """Register all read-only tools on the Pydantic AI agent."""
        for tool_func in ALL_TOOLS:
            self.agent.tool(tool_func)

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
        deps = self._build_deps()
        result = await self.agent.run(prompt, deps=deps)
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
