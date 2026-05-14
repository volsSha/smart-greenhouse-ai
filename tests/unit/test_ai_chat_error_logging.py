"""Tests for AI chat API error logging."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_db_session
from app.main import app


@pytest.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_chat_logs_unexpected_ai_failures(client: AsyncClient) -> None:
    session = AsyncMock()
    session.rollback = AsyncMock()
    session.commit = AsyncMock()
    session_factory = MagicMock()

    async def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session
    app.state.session_factory = session_factory

    try:
        with (
            patch("app.api.ai_chat.GreenhouseAIAgent") as agent_class,
            patch("app.api.ai_chat.create_debug_log_best_effort", new_callable=AsyncMock) as log_error,
            patch("app.main.create_debug_log_best_effort", new_callable=AsyncMock),
        ):
            agent_class.return_value.chat = AsyncMock(side_effect=RuntimeError("Запит не виконано"))

            response = await client.post(
                "/api/ai/chat",
                json={
                    "message": "Включи в зоні zone-01 світло",
                    "scope": {"zone_id": "zone-01"},
                },
            )
    finally:
        app.dependency_overrides.clear()
        if hasattr(app.state, "session_factory"):
            delattr(app.state, "session_factory")

    assert response.status_code == 500
    session.rollback.assert_awaited_once()
    log_error.assert_awaited_once()
    kwargs = log_error.await_args.kwargs
    assert kwargs["level"] == "error"
    assert kwargs["component"] == "ai_agent"
    assert kwargs["event_type"] == "ai_chat_failed"
    assert kwargs["metadata"]["message"] == "Включи в зоні zone-01 світло"
    assert kwargs["metadata"]["scope"] == {"group_id": None, "greenhouse_id": None, "zone_id": "zone-01"}
