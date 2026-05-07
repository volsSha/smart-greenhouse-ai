"""Tests for worker reindex job orchestration."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from services.worker.jobs import run_reindex_job


@pytest.mark.asyncio
async def test_worker_reindex_job_processes_stale_documents() -> None:
    reindexer = AsyncMock()
    reindexer.reindex_stale = AsyncMock(return_value=[{"status": "success"}, {"status": "skipped"}])

    result = await run_reindex_job(reindexer)

    assert result.name == "rag_reindex"
    assert result.status == "ok"
    assert result.processed == 2
    assert result.errors == []
    reindexer.reindex_stale.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_reindex_job_records_failures_without_raising() -> None:
    reindexer = AsyncMock()
    reindexer.reindex_stale = AsyncMock(side_effect=RuntimeError("embedding provider down"))

    result = await run_reindex_job(reindexer)

    assert result.status == "failed"
    assert result.processed == 0
    assert result.errors == ["embedding provider down"]
