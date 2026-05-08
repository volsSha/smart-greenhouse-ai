"""RAG search tool for the AI agent.

Provides semantic search over the agronomic knowledge base.
"""

from __future__ import annotations

import uuid

from pydantic_ai import RunContext

from app.services.ai_agent.tools.deps import ToolDeps
from app.services.rag.embedding_client import EmbeddingClient


async def search_plant_knowledge(
    ctx: RunContext[ToolDeps],
    query: str,
    group_id: str | None = None,
) -> list[dict]:
    """Search the agronomic knowledge base for relevant information.

    Use this tool to find domain-specific knowledge about plant care,
    disease symptoms, optimal growth conditions, and greenhouse management
    practices. Results include source attribution.

    Args:
        query: The search query describing what knowledge to retrieve.
        group_id: Optional group ID to scope the search.

    Returns:
        List of search results with content, document_title, score, and metadata.
    """
    # Generate embedding for the query
    settings = ctx.deps.settings if hasattr(ctx.deps, "settings") else None
    api_key = settings.openrouter.api_key if settings else ""
    base_url = settings.openrouter.base_url if settings else "https://openrouter.ai/api/v1"
    embedding_model = settings.openrouter.embedding_model if settings else "text-embedding-3-small"
    embedding_dimension = settings.openrouter.embedding_dimension if settings else 1536

    embedding_client = EmbeddingClient(
        api_key=api_key,
        base_url=base_url,
        model=embedding_model,
        dimension=embedding_dimension,
    )

    query_embeddings = await embedding_client.embed([query])
    query_embedding = query_embeddings[0]

    group_uuid = uuid.UUID(group_id) if group_id else None

    results = await ctx.deps.rag_repo.search(
        query_embedding=query_embedding,
        limit=10,
        group_id=group_uuid,
    )

    return [
        {
            "content": r["content"],
            "document_title": r["document_title"],
            "score": r["score"],
            "metadata": r["metadata"],
        }
        for r in results
    ]
