"""Repository for application debug log entries."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.debug_log import DebugLog

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = ("authorization", "api_key", "token", "password", "secret", "key")


def sanitize_metadata(value: Any) -> Any:
    """Redact sensitive values from nested metadata."""
    if isinstance(value, dict):
        return {
            str(key): "[redacted]" if any(term in str(key).lower() for term in SENSITIVE_KEYS) else sanitize_metadata(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_metadata(item) for item in value]
    return value


class DebugLogRepository:
    """Persist debug log entries."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        level: str,
        event_type: str,
        component: str,
        message: str,
        path: str | None = None,
        method: str | None = None,
        status_code: int | None = None,
        duration_ms: float | None = None,
        request_id: str | None = None,
        error_type: str | None = None,
        stack_trace: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DebugLog:
        log = DebugLog(
            level=level,
            event_type=event_type,
            component=component,
            message=message,
            path=path,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            request_id=request_id,
            error_type=error_type,
            stack_trace=stack_trace,
            log_metadata=sanitize_metadata(metadata),
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def list(
        self,
        *,
        level: str | None = None,
        component: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
    ) -> list[DebugLog]:
        stmt = select(DebugLog).order_by(DebugLog.created_at.desc())
        if level is not None:
            stmt = stmt.where(DebugLog.level == level)
        if component is not None:
            stmt = stmt.where(DebugLog.component == component)
        if event_type is not None:
            stmt = stmt.where(DebugLog.event_type == event_type)

        result = await self.session.execute(stmt.limit(limit))
        return list(result.scalars().all())


async def create_debug_log_best_effort(
    session_factory: async_sessionmaker[AsyncSession],
    **kwargs: Any,
) -> None:
    """Persist a debug log entry without breaking the request path."""
    try:
        async with session_factory() as session:
            repo = DebugLogRepository(session)
            await repo.create(**kwargs)
            await session.commit()
    except Exception:
        logger.warning("Failed to persist debug log", exc_info=True)
