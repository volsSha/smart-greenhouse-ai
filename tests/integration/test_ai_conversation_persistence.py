"""Integration-style tests for AI conversation persistence plumbing."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai import Agent, UnexpectedModelBehavior
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AppSettings, DatabaseSettings, InfluxDBSettings, MQTTSettings, OpenRouterSettings, Settings
from app.repositories.ai_conversation_repository import AIConversationRepository
from app.repositories.ai_tool_log_repository import AIToolLogRepository
from app.services.ai_agent.agent import GreenhouseAIAgent
from app.services.ai_agent.models import AIResponse, AIResponseStatus, AIScope


def _make_mock_session() -> AsyncSession:
    """Create a mock AsyncSession with async methods."""
    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result)
    return session


def _settings() -> Settings:
    """Return safe test settings for agent construction."""
    return Settings(
        database=DatabaseSettings(user="test", password="test", db="test"),
        influxdb=InfluxDBSettings(token="test"),
        mqtt=MQTTSettings(),
        openrouter=OpenRouterSettings(api_key="test-key", model="test-model"),
        app=AppSettings(debug=True),
    )


@pytest.mark.asyncio
async def test_conversation_repository_create_and_add_message() -> None:
    """Repository creates scoped conversations and messages with mock session."""
    session = _make_mock_session()
    repo = AIConversationRepository(session)
    group_id = uuid.uuid4()

    conversation = await repo.create_conversation(AIScope(group_id=str(group_id)))
    message = await repo.add_message(
        conversation.id,
        role="user",
        content="How is the group?",
    )

    assert session.add.call_count == 2
    assert session.flush.await_count == 2
    assert conversation.group_id == group_id
    assert message.conversation_id == conversation.id
    assert message.role == "user"


@pytest.mark.asyncio
async def test_conversation_repository_ignores_display_scope_ids() -> None:
    """Repository does not crash when chat scope uses display identifiers."""
    session = _make_mock_session()
    repo = AIConversationRepository(session)

    conversation = await repo.create_conversation(
        AIScope(group_id="group-001", greenhouse_id="gh-001", zone_id="zone-01")
    )

    assert conversation.group_id is None
    assert conversation.greenhouse_id is None
    assert conversation.zone_id is None


@pytest.mark.asyncio
async def test_tool_log_repository_create() -> None:
    """Tool log repository persists tool-call ORM objects."""
    session = _make_mock_session()
    repo = AIToolLogRepository(session)
    conversation_id = uuid.uuid4()

    tool_call = await repo.log_tool_call(
        conversation_id=conversation_id,
        tool_name="get_group_overview",
        arguments={"group_id": "g1"},
        result={"summary": "ok"},
        status="ok",
        error=None,
    )

    assert session.add.called
    assert session.flush.await_count == 1
    assert tool_call.conversation_id == conversation_id
    assert tool_call.tool_name == "get_group_overview"


def test_agent_default_uses_configured_openrouter_model() -> None:
    """Default agent construction uses configured model, not the DB session."""
    session = _make_mock_session()

    service = GreenhouseAIAgent(session, settings=_settings())

    assert service.agent._model.model_name == "test-model"


@pytest.mark.asyncio
async def test_agent_rebuilds_when_selected_model_differs() -> None:
    """Selected model comparison uses Pydantic AI's public model_name."""
    session = _make_mock_session()
    selected_settings = SimpleNamespace(
        selected_chat_model="anthropic/claude-sonnet-4",
        selected_model_available=True,
    )
    service = GreenhouseAIAgent(session, settings=_settings(), agent=MagicMock())
    service.agent._model = SimpleNamespace(model_name="test-model")
    service.register_tools = MagicMock()
    service._build_agent = MagicMock(return_value=MagicMock())

    service.session.execute.return_value.scalar_one_or_none.return_value = selected_settings

    await service._ensure_agent_uses_selected_model()

    service._build_agent.assert_called_once_with(_settings(), "anthropic/claude-sonnet-4")
    service.register_tools.assert_called_once()


@pytest.mark.asyncio
async def test_agent_chat_returns_fallback_for_invalid_model_output() -> None:
    """Invalid structured model output is returned as a safe chat response, not a 500."""
    session = _make_mock_session()
    conversation_id = uuid.uuid4()
    fake_conversation = SimpleNamespace(id=conversation_id)
    fake_agent = MagicMock()
    fake_agent.run = AsyncMock(side_effect=UnexpectedModelBehavior("bad output"))
    fake_agent._model = SimpleNamespace(model_name="test-model")

    service = GreenhouseAIAgent(session, settings=_settings(), agent=fake_agent)
    service.conversation_repository.create_conversation = AsyncMock(return_value=fake_conversation)
    service.conversation_repository.add_message = AsyncMock()

    response = await service.chat(message="Привіт", scope=AIScope())

    assert response.status == AIResponseStatus.INSUFFICIENT_DATA
    assert "required schema" in response.summary
    assert service.conversation_repository.add_message.await_count == 2
    assistant_call = service.conversation_repository.add_message.await_args_list[1]
    assert assistant_call.kwargs["model"] == "test-model"


@pytest.mark.asyncio
async def test_agent_chat_persists_user_and_assistant_messages() -> None:
    """GreenhouseAIAgent persists a chat turn while using TestModel double."""
    from app.services.ai_agent.tools.deps import ToolDeps

    session = _make_mock_session()
    conversation_id = uuid.uuid4()
    fake_conversation = SimpleNamespace(id=conversation_id)
    output = AIResponse(
        scope=AIScope(group_id="group-001"),
        status=AIResponseStatus.INSUFFICIENT_DATA,
        summary="No telemetry tools are registered yet.",
        observations=[],
        recommendations=["Register read-only tools before answering live state questions."],
        proposed_actions=[],
    )
    test_agent = Agent(
        TestModel(custom_output_args=output),
        output_type=AIResponse,
        deps_type=ToolDeps,
    )
    service = GreenhouseAIAgent(session, settings=_settings(), agent=test_agent)
    service.conversation_repository.create_conversation = AsyncMock(return_value=fake_conversation)
    service.conversation_repository.add_message = AsyncMock()

    response = await service.chat(
        message="How is group 001?",
        scope=AIScope(group_id="group-001"),
    )

    assert response.status == AIResponseStatus.INSUFFICIENT_DATA
    service.conversation_repository.create_conversation.assert_awaited_once()
    assert service.conversation_repository.add_message.await_count == 2
    first_call = service.conversation_repository.add_message.await_args_list[0]
    second_call = service.conversation_repository.add_message.await_args_list[1]
    assert first_call.kwargs["role"] == "user"
    assert second_call.kwargs["role"] == "assistant"
    assert "No telemetry tools" in second_call.kwargs["content"]
