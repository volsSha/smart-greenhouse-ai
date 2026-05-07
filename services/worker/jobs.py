"""Background jobs for Smart Greenhouse maintenance tasks."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


class Reindexer(Protocol):
    async def reindex_stale(self) -> list[dict]: ...
    async def reindex_all(self) -> list[dict]: ...


@dataclass(frozen=True)
class JobResult:
    name: str
    status: str
    processed: int
    errors: list[str]


async def run_reindex_job(reindexer: Reindexer, stale_only: bool = True) -> JobResult:
    """Run the RAG reindex job and return a durable summary."""
    try:
        results = await (reindexer.reindex_stale() if stale_only else reindexer.reindex_all())
    except Exception as exc:
        logger.warning("RAG reindex job failed", exc_info=True)
        return JobResult("rag_reindex", "failed", 0, [str(exc)])

    errors = [str(result.get("reason", "unknown")) for result in results if result.get("status") == "error"]
    return JobResult(
        name="rag_reindex",
        status="failed" if errors else "ok",
        processed=len(results),
        errors=errors,
    )
