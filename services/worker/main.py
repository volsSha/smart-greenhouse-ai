"""Standalone worker process entry point."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.config import get_settings
from app.dependencies import create_db_engine
from app.repositories.rag_repository import RAGRepository
from app.services.rag.embedding_client import EmbeddingClient
from app.services.rag.reindex_service import ReindexService
from services.worker.jobs import run_reindex_job
from sqlalchemy.ext.asyncio import async_sessionmaker

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smart Greenhouse worker")
    parser.add_argument("--job", choices=["rag-reindex"], default="rag-reindex")
    parser.add_argument("--all", action="store_true", help="Reindex all documents instead of stale documents")
    return parser.parse_args()


async def run_worker() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    settings = get_settings()
    engine = create_db_engine(settings)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        if args.job == "rag-reindex":
            repo = RAGRepository(session)
            embeddings = EmbeddingClient(settings.openrouter.api_key)
            result = await run_reindex_job(ReindexService(repo, embeddings), stale_only=not args.all)
            await session.commit()
            logger.info("Worker job %s finished: %s", result.name, result.status)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_worker())
