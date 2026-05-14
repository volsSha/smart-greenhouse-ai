"""Tests for debug log repository helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.debug_log_repository import DebugLogRepository, sanitize_metadata


def test_sanitize_metadata_redacts_nested_sensitive_values() -> None:
    sanitized = sanitize_metadata(
        {
            "authorization": "Bearer secret",
            "nested": {"api_key": "secret", "ok": "value"},
            "items": [{"password": "secret"}],
        }
    )

    assert sanitized["authorization"] == "[redacted]"
    assert sanitized["nested"]["api_key"] == "[redacted]"
    assert sanitized["nested"]["ok"] == "value"
    assert sanitized["items"][0]["password"] == "[redacted]"


@pytest.mark.asyncio
async def test_list_filters_and_returns_scalars() -> None:
    session = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["log"]
    session.execute = AsyncMock(return_value=result)
    repo = DebugLogRepository(session)

    logs = await repo.list(
        level="error",
        component="ai_agent",
        event_type="ai_chat_failed",
        limit=25,
    )

    assert logs == ["log"]
    session.execute.assert_awaited_once()
    stmt = session.execute.await_args.args[0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "debug_log.level = 'error'" in compiled
    assert "debug_log.component = 'ai_agent'" in compiled
    assert "debug_log.event_type = 'ai_chat_failed'" in compiled
    assert "ORDER BY debug_log.created_at DESC" in compiled
    assert "LIMIT 25" in compiled
