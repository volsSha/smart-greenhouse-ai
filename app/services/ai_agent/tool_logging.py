"""Tool invocation logging with sensitive-data sanitization."""

from __future__ import annotations

import time
import uuid
from collections.abc import Mapping
from typing import Any

from app.models.ai import AIToolCall
from app.repositories.ai_tool_log_repository import AIToolLogRepository

SENSITIVE_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
)
VECTOR_KEY_FRAGMENTS = ("embedding", "embeddings", "vector")
MAX_STRING_LENGTH = 500
MAX_LIST_ITEMS = 20


def sanitize_for_tool_log(value: Any) -> Any:
    """Remove credentials and large vector payloads from persisted tool logs."""
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_str = str(key)
            lowered = key_str.lower()
            if any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS):
                sanitized[key_str] = "[REDACTED]"
            elif any(fragment in lowered for fragment in VECTOR_KEY_FRAGMENTS):
                sanitized[key_str] = "[OMITTED]"
            else:
                sanitized[key_str] = sanitize_for_tool_log(item)
        return sanitized
    if isinstance(value, list):
        if value and all(isinstance(item, int | float) for item in value):
            return f"[numeric-list:{len(value)}]"
        return [sanitize_for_tool_log(item) for item in value[:MAX_LIST_ITEMS]]
    if isinstance(value, tuple):
        return [sanitize_for_tool_log(item) for item in value[:MAX_LIST_ITEMS]]
    if isinstance(value, str) and len(value) > MAX_STRING_LENGTH:
        return f"{value[:MAX_STRING_LENGTH]}...[truncated]"
    return value


class ToolCallLogger:
    """Persist sanitized tool-call logs for AI conversation explainability."""

    def __init__(self, repository: AIToolLogRepository) -> None:
        self.repository = repository

    async def log_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: Any,
        status: str,
        error: str | None,
        conversation_id: uuid.UUID,
        duration_ms: int | None = None,
    ) -> AIToolCall:
        """Sanitize and persist a tool invocation."""
        stored_result = sanitize_for_tool_log(result)
        if stored_result is not None and not isinstance(stored_result, dict):
            stored_result = {"summary": stored_result}

        if duration_ms is not None:
            if stored_result is None:
                stored_result = {}
            stored_result["duration_ms"] = duration_ms

        return await self.repository.log_tool_call(
            conversation_id=conversation_id,
            tool_name=tool_name,
            arguments=sanitize_for_tool_log(arguments),
            result=stored_result,
            status=status,
            error=error,
        )

    async def run_and_log(
        self,
        conversation_id: uuid.UUID,
        tool_name: str,
        arguments: dict[str, Any],
        func,
    ) -> Any:
        """Execute a tool-like callable and log success or failure."""
        started = time.perf_counter()
        try:
            result = await func(**arguments)
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            await self.log_tool_call(
                tool_name=tool_name,
                arguments=arguments,
                result=None,
                status="error",
                error=str(exc),
                conversation_id=conversation_id,
                duration_ms=duration_ms,
            )
            raise

        duration_ms = int((time.perf_counter() - started) * 1000)
        await self.log_tool_call(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            status="ok",
            error=None,
            conversation_id=conversation_id,
            duration_ms=duration_ms,
        )
        return result
