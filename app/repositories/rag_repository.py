"""Async CRUD repository for RAG documents and chunks with pgvector search."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rag import RAGChunk, RAGDocument


class RAGRepository:
    """Repository for RAG document CRUD and vector similarity search."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- Document CRUD ---

    async def create_document(
        self,
        *,
        title: str,
        content: str,
        source_type: str | None = None,
        source_url: str | None = None,
        group_id: uuid.UUID | None = None,
        metadata_: dict | None = None,
    ) -> RAGDocument:
        """Create a new RAG document."""
        document = RAGDocument(
            title=title,
            content=content,
            source_type=source_type,
            source_url=source_url,
            group_id=group_id,
            metadata_=metadata_,
        )
        self.session.add(document)
        await self.session.flush()
        return document

    async def get_document(self, document_id: uuid.UUID) -> RAGDocument | None:
        """Fetch a single document by its UUID."""
        return await self.session.get(RAGDocument, document_id)

    async def list_documents(
        self,
        group_id: uuid.UUID | None = None,
    ) -> list[RAGDocument]:
        """List documents, optionally filtered by group_id."""
        stmt = select(RAGDocument).order_by(RAGDocument.created_at.desc())
        if group_id is not None:
            stmt = stmt.where(RAGDocument.group_id == group_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_document(self, document_id: uuid.UUID) -> bool:
        """Delete a document and its chunks. Returns True if found and deleted."""
        document = await self.session.get(RAGDocument, document_id)
        if document is None:
            return False
        await self.session.delete(document)
        await self.session.flush()
        return True

    # --- Chunk operations ---

    async def add_chunks(
        self,
        document_id: uuid.UUID,
        chunks: list[dict[str, Any]],
    ) -> list[RAGChunk]:
        """Add embedding chunks for a document.

        Args:
            document_id: The parent document UUID.
            chunks: List of dicts with keys:
                - chunk_index (int)
                - content (str)
                - embedding (list[float] | None)
                - embedding_model (str | None)
                - metadata (dict | None)

        Returns:
            The created RAGChunk instances.
        """
        chunk_models = []
        for chunk_data in chunks:
            chunk = RAGChunk(
                document_id=document_id,
                chunk_index=chunk_data["chunk_index"],
                content=chunk_data["content"],
                embedding=chunk_data.get("embedding"),
                embedding_model=chunk_data.get("embedding_model"),
                metadata_=chunk_data.get("metadata"),
            )
            self.session.add(chunk)
            chunk_models.append(chunk)
        await self.session.flush()
        return chunk_models

    async def delete_chunks_for_document(self, document_id: uuid.UUID) -> int:
        """Delete all chunks for a document. Returns the number of deleted chunks."""
        stmt = delete(RAGChunk).where(RAGChunk.document_id == document_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    # --- Vector search ---

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        group_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar chunks using cosine similarity.

        Args:
            query_embedding: The query vector.
            limit: Maximum number of results.
            group_id: Optional group filter.

        Returns:
            List of dicts with keys: content, document_title, score, metadata.
        """
        # Build the query with cosine distance (1 - cosine_similarity)
        # Lower cosine distance = higher similarity
        stmt = (
            select(
                RAGChunk.content,
                RAGDocument.title.label("document_title"),
                RAGChunk.embedding.cosine_distance(query_embedding).label("score"),
                RAGChunk.metadata_,
            )
            .join(RAGChunk.document)
            .where(RAGChunk.embedding.isnot(None))
            .order_by("score")
            .limit(limit)
        )

        if group_id is not None:
            stmt = stmt.where(RAGDocument.group_id == group_id)

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "content": row.content,
                "document_title": row.document_title,
                "score": float(row.score),
                "metadata": row.metadata_,
            }
            for row in rows
        ]

    async def list_all_documents_with_embedding_model(self) -> list[dict[str, Any]]:
        """List all documents with their current embedding model for reindex detection.

        Returns:
            List of dicts with keys: id, embedding_model.
        """
        stmt = (
            select(
                RAGDocument.id,
                RAGChunk.embedding_model,
            )
            .outerjoin(RAGChunk, RAGDocument.id == RAGChunk.document_id)
            .group_by(RAGDocument.id, RAGChunk.embedding_model)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "id": row.id,
                "embedding_model": row.embedding_model,
            }
            for row in rows
        ]
