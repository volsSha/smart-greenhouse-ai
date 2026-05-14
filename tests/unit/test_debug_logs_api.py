"""Tests for debug-log API endpoints."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_db_session
from app.main import app


@pytest.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_list_debug_logs_returns_metadata_alias(client: AsyncClient) -> None:
    log = SimpleNamespace(
        id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        level="error",
        event_type="ai_chat_failed",
        component="ai_agent",
        message="Запит не виконано",
        path="/api/ai/chat",
        method="POST",
        status_code=500,
        duration_ms=None,
        request_id="req-1",
        error_type="RuntimeError",
        stack_trace="trace",
        log_metadata={"message": "Включи в зоні zone-01 світло"},
    )
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [log]
    session.execute = AsyncMock(return_value=result)

    async def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        response = await client.get(
            "/api/debug-logs",
            params={"level": "error", "component": "ai_agent", "limit": 10},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data[0]["metadata"] == {"message": "Включи в зоні zone-01 світло"}
    assert "log_metadata" not in data[0]
    assert data[0]["component"] == "ai_agent"
