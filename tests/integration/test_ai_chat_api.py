"""Integration tests for the AI chat API endpoints.

Tests the REST endpoints for sending chat messages, listing conversations,
fetching conversation details, and retrieving tool call logs. All tests
use a minimal test app with dependency overrides to inject mock sessions.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ai_chat import router as ai_chat_router
from app.dependencies import get_db_session
from app.services.ai_agent.models import AIResponse, AIResponseStatus, AIScope


# --- Build a minimal test app with just the AI chat router ---
from fastapi import FastAPI

ai_test_app = FastAPI()
ai_test_app.include_router(ai_chat_router)

# Module-level mock session for the dependency override
_mock_session: MagicMock | None = None


async def _session_override() -> AsyncGenerator[AsyncSession, None]:
    """Yield the module-level mock session for dependency override."""
    assert _mock_session is not None
    yield _mock_session  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_mock_session() -> MagicMock:
    """Create a mock AsyncSession."""
    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    session.close = AsyncMock()
    return session


def _fake_conversation(conversation_id: uuid.UUID | None = None) -> SimpleNamespace:
    """Create a fake conversation ORM object."""
    conv_id = conversation_id or uuid.uuid4()
    return SimpleNamespace(
        id=conv_id,
        group_id=None,
        greenhouse_id=None,
        zone_id=None,
        user_id=None,
        title="Test conversation",
        created_at=None,
        messages=[],
    )


def _fake_message(
    conversation_id: uuid.UUID,
    role: str = "user",
    content: str = "Hello",
) -> SimpleNamespace:
    """Create a fake message ORM object."""
    return SimpleNamespace(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        role=role,
        content=content,
        model=None,
        token_input=None,
        token_output=None,
        created_at=None,
    )


def _fake_tool_call(conversation_id: uuid.UUID) -> SimpleNamespace:
    """Create a fake tool call ORM object."""
    return SimpleNamespace(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        tool_name="get_group_overview",
        arguments={"group_id": "group-001"},
        result={"summary": "3 greenhouses"},
        status="ok",
        error=None,
    )


_SAMPLE_AI_RESPONSE = AIResponse(
    scope=AIScope(group_id="group-001"),
    status=AIResponseStatus.OK,
    summary="All greenhouses in group-001 are operating normally.",
    observations=["Temperature averages 23C across all zones."],
    recommendations=["Consider adjusting ventilation for the upcoming heat wave."],
    proposed_actions=[],
)


# ---------------------------------------------------------------------------
# POST /api/ai/chat
# ---------------------------------------------------------------------------


class TestChatEndpoint:
    """Tests for the POST /api/ai/chat endpoint."""

    @pytest.mark.anyio
    async def test_chat_returns_structured_response(self) -> None:
        """Chat endpoint returns a valid AIResponse with summary and observations."""
        global _mock_session
        _mock_session = _make_mock_session()
        ai_test_app.dependency_overrides[get_db_session] = _session_override

        with patch("app.api.ai_chat.GreenhouseAIAgent") as MockAgent:
            mock_agent_instance = MockAgent.return_value
            mock_agent_instance.chat = AsyncMock(return_value=_SAMPLE_AI_RESPONSE)

            transport = ASGITransport(app=ai_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/ai/chat",
                    json={
                        "message": "How is group 001?",
                        "scope": {"group_id": "group-001"},
                    },
                )

        ai_test_app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"] == _SAMPLE_AI_RESPONSE.summary
        assert data["status"] == "ok"
        assert len(data["observations"]) == 1
        assert data["scope"]["group_id"] == "group-001"

    @pytest.mark.anyio
    async def test_chat_with_existing_conversation_id(self) -> None:
        """Chat endpoint passes conversation_id to the agent service."""
        global _mock_session
        _mock_session = _make_mock_session()
        conv_id = str(uuid.uuid4())
        ai_test_app.dependency_overrides[get_db_session] = _session_override

        with patch("app.api.ai_chat.GreenhouseAIAgent") as MockAgent:
            mock_agent_instance = MockAgent.return_value
            mock_agent_instance.chat = AsyncMock(return_value=_SAMPLE_AI_RESPONSE)

            transport = ASGITransport(app=ai_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/ai/chat",
                    json={
                        "message": "Follow up question",
                        "conversation_id": conv_id,
                    },
                )

        ai_test_app.dependency_overrides.clear()

        assert resp.status_code == 200
        mock_agent_instance.chat.assert_awaited_once()
        call_kwargs = mock_agent_instance.chat.await_args.kwargs
        assert str(call_kwargs["conversation_id"]) == conv_id

    @pytest.mark.anyio
    async def test_chat_with_proposed_actions(self) -> None:
        """Chat endpoint returns proposed actions with requires_confirmation=True."""
        global _mock_session
        response_with_actions = AIResponse(
            scope=AIScope(
                group_id="group-001",
                greenhouse_id="gh-001",
                zone_id="zone-01",
            ),
            status=AIResponseStatus.OK,
            summary="Soil moisture is low.",
            observations=["Soil moisture at 20%."],
            recommendations=[],
            proposed_actions=[
                {
                    "actuator": "pump",
                    "action": "on",
                    "duration_seconds": 30,
                    "reason": "Soil moisture below threshold.",
                    "zone_id": "zone-01",
                }
            ],
        )
        _mock_session = _make_mock_session()
        ai_test_app.dependency_overrides[get_db_session] = _session_override

        with patch("app.api.ai_chat.GreenhouseAIAgent") as MockAgent:
            mock_agent_instance = MockAgent.return_value
            mock_agent_instance.chat = AsyncMock(return_value=response_with_actions)

            transport = ASGITransport(app=ai_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/ai/chat",
                    json={"message": "Check soil moisture"},
                )

        ai_test_app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["proposed_actions"]) == 1
        assert data["proposed_actions"][0]["actuator"] == "pump"
        assert data["proposed_actions"][0]["requires_confirmation"] is True

    @pytest.mark.anyio
    async def test_chat_commits_session(self) -> None:
        """Chat endpoint commits the session after successful response."""
        global _mock_session
        _mock_session = _make_mock_session()
        ai_test_app.dependency_overrides[get_db_session] = _session_override

        with patch("app.api.ai_chat.GreenhouseAIAgent") as MockAgent:
            mock_agent_instance = MockAgent.return_value
            mock_agent_instance.chat = AsyncMock(return_value=_SAMPLE_AI_RESPONSE)

            transport = ASGITransport(app=ai_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.post("/api/ai/chat", json={"message": "test"})

        ai_test_app.dependency_overrides.clear()

        _mock_session.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# GET /api/ai/conversations
# ---------------------------------------------------------------------------


class TestListConversationsEndpoint:
    """Tests for the GET /api/ai/conversations endpoint."""

    @pytest.mark.anyio
    async def test_list_conversations_returns_empty_list(self) -> None:
        """Returns empty list when no conversations exist."""
        global _mock_session
        _mock_session = _make_mock_session()
        ai_test_app.dependency_overrides[get_db_session] = _session_override

        with patch("app.api.ai_chat.AIConversationRepository") as MockRepo:
            MockRepo.return_value.list_conversations = AsyncMock(return_value=[])

            transport = ASGITransport(app=ai_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/ai/conversations")

        ai_test_app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_list_conversations_returns_conversations(self) -> None:
        """Returns conversation summaries."""
        global _mock_session
        conv1 = _fake_conversation()
        conv2 = _fake_conversation()
        _mock_session = _make_mock_session()
        ai_test_app.dependency_overrides[get_db_session] = _session_override

        with patch("app.api.ai_chat.AIConversationRepository") as MockRepo:
            MockRepo.return_value.list_conversations = AsyncMock(
                return_value=[conv1, conv2]
            )

            transport = ASGITransport(app=ai_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/ai/conversations")

        ai_test_app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["title"] == "Test conversation"


# ---------------------------------------------------------------------------
# GET /api/ai/conversations/{conversation_id}
# ---------------------------------------------------------------------------


class TestGetConversationEndpoint:
    """Tests for the GET /api/ai/conversations/{id} endpoint."""

    @pytest.mark.anyio
    async def test_get_conversation_returns_messages(self) -> None:
        """Returns a conversation with its messages."""
        global _mock_session
        conv_id = uuid.uuid4()
        conv = _fake_conversation(conv_id)
        conv.messages = [
            _fake_message(conv_id, "user", "Hello"),
            _fake_message(conv_id, "assistant", json.dumps({
                "summary": "Hi there!",
                "observations": [],
                "recommendations": [],
                "proposed_actions": [],
            })),
        ]
        _mock_session = _make_mock_session()
        ai_test_app.dependency_overrides[get_db_session] = _session_override

        with patch("app.api.ai_chat.AIConversationRepository") as MockRepo:
            MockRepo.return_value.get_conversation = AsyncMock(return_value=conv)

            transport = ASGITransport(app=ai_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/api/ai/conversations/{conv_id}")

        ai_test_app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"

    @pytest.mark.anyio
    async def test_get_conversation_not_found(self) -> None:
        """Returns 404 for a non-existent conversation."""
        global _mock_session
        _mock_session = _make_mock_session()
        ai_test_app.dependency_overrides[get_db_session] = _session_override

        with patch("app.api.ai_chat.AIConversationRepository") as MockRepo:
            MockRepo.return_value.get_conversation = AsyncMock(return_value=None)

            transport = ASGITransport(app=ai_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/api/ai/conversations/{uuid.uuid4()}")

        ai_test_app.dependency_overrides.clear()

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/ai/tool-calls/{conversation_id}
# ---------------------------------------------------------------------------


class TestToolCallsEndpoint:
    """Tests for the GET /api/ai/tool-calls/{conversation_id} endpoint."""

    @pytest.mark.anyio
    async def test_get_tool_calls_returns_empty_list(self) -> None:
        """Returns empty list when no tool calls exist for a conversation."""
        global _mock_session
        conv_id = uuid.uuid4()
        _mock_session = _make_mock_session()
        ai_test_app.dependency_overrides[get_db_session] = _session_override

        with patch("app.api.ai_chat.AIToolLogRepository") as MockRepo:
            MockRepo.return_value.get_tool_calls = AsyncMock(return_value=[])

            transport = ASGITransport(app=ai_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/api/ai/tool-calls/{conv_id}")

        ai_test_app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_get_tool_calls_returns_calls(self) -> None:
        """Returns tool call logs for a conversation."""
        global _mock_session
        conv_id = uuid.uuid4()
        tool_call = _fake_tool_call(conv_id)
        _mock_session = _make_mock_session()
        ai_test_app.dependency_overrides[get_db_session] = _session_override

        with patch("app.api.ai_chat.AIToolLogRepository") as MockRepo:
            MockRepo.return_value.get_tool_calls = AsyncMock(return_value=[tool_call])

            transport = ASGITransport(app=ai_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/api/ai/tool-calls/{conv_id}")

        ai_test_app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["tool_name"] == "get_group_overview"
        assert data[0]["status"] == "ok"
        assert data[0]["arguments"]["group_id"] == "group-001"
