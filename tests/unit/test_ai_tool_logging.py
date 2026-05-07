"""Unit tests for AI tool-call logging."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.services.ai_agent.tool_logging import ToolCallLogger, sanitize_for_tool_log


def test_sanitize_for_tool_log_redacts_credentials_and_vectors() -> None:
    """Tool logs must not persist secrets or embedding vectors."""
    sanitized = sanitize_for_tool_log(
        {
            "api_key": "secret-key",
            "nested": {"password": "secret-pass", "ok": "value"},
            "embedding": [0.1, 0.2, 0.3],
            "readings": [1, 2, 3],
        }
    )

    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["password"] == "[REDACTED]"
    assert sanitized["nested"]["ok"] == "value"
    assert sanitized["embedding"] == "[OMITTED]"
    assert sanitized["readings"] == "[numeric-list:3]"


@pytest.mark.asyncio
async def test_tool_call_logger_persists_sanitized_payload() -> None:
    """ToolCallLogger delegates sanitized data to the repository."""
    repo = AsyncMock()
    logger = ToolCallLogger(repo)
    conversation_id = uuid.uuid4()

    await logger.log_tool_call(
        tool_name="get_zone_state",
        arguments={"group_id": "g1", "token": "secret"},
        result={"summary": "ok", "vector": [1.0, 2.0]},
        status="ok",
        error=None,
        conversation_id=conversation_id,
        duration_ms=12,
    )

    repo.log_tool_call.assert_awaited_once()
    kwargs = repo.log_tool_call.await_args.kwargs
    assert kwargs["conversation_id"] == conversation_id
    assert kwargs["arguments"]["token"] == "[REDACTED]"
    assert kwargs["result"]["vector"] == "[OMITTED]"
    assert kwargs["result"]["duration_ms"] == 12


@pytest.mark.asyncio
async def test_run_and_log_records_errors() -> None:
    """run_and_log records failed tool calls before re-raising."""
    repo = AsyncMock()
    logger = ToolCallLogger(repo)
    conversation_id = uuid.uuid4()

    async def failing_tool(group_id: str) -> dict:
        raise RuntimeError(f"missing data for {group_id}")

    with pytest.raises(RuntimeError):
        await logger.run_and_log(
            conversation_id=conversation_id,
            tool_name="get_group_overview",
            arguments={"group_id": "g1"},
            func=failing_tool,
        )

    kwargs = repo.log_tool_call.await_args.kwargs
    assert kwargs["status"] == "error"
    assert "missing data" in kwargs["error"]
