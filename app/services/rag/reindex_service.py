"""Reindex service for rebuilding RAG embeddings.

Handles re-chunking and re-embedding documents, including detection
of documents with outdated embedding models.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from app.services.rag.chunker import chunk_text

if TYPE_CHECKING:
    from app.services.rag.embedding_client import EmbeddingClient
    from app.repositories.rag_repository import RAGRepository

logger = logging.getLogger(__name__)


class ReindexService:
    """Service for reindexing RAG documents."""

    def __init__(
        self,
        repo: RAGRepository,
        embedding_client: EmbeddingClient,
    ) -> None:
        self.repo = repo
        self.embedding_client = embedding_client

    async def reindex_document(self, document_id: uuid.UUID) -> dict:
        """Re-chunk and re-embed a single document.

        Args:
            document_id: The document to reindex.

        Returns:
            Dict with keys: document_id, chunks_created, status.

        Raises:
            ValueError: If the document is not found.
        """
        document = await self.repo.get_document(document_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found")

        if not document.content:
            return {
                "document_id": str(document_id),
                "chunks_created": 0,
                "status": "skipped",
                "reason": "no content",
            }

        # Delete existing chunks
        deleted = await self.repo.delete_chunks_for_document(document_id)
        logger.info(
            "Deleted %d old chunks for document %s",
            deleted,
            document_id,
        )

        # Re-chunk
        chunks = chunk_text(document.content)
        if not chunks:
            return {
                "document_id": str(document_id),
                "chunks_created": 0,
                "status": "skipped",
                "reason": "no chunks produced",
            }

        # Generate embeddings
        embeddings = await self.embedding_client.embed(chunks)

        # Build chunk data
        chunk_data_list = []
        for i, (chunk_text_val, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_data_list.append(
                {
                    "chunk_index": i,
                    "content": chunk_text_val,
                    "embedding": embedding,
                    "embedding_model": self.embedding_client.model_name,
                    "metadata": None,
                }
            )

        # Store chunks
        created_chunks = await self.repo.add_chunks(document_id, chunk_data_list)

        logger.info(
            "Reindexed document %s: %d chunks created with model %s",
            document_id,
            len(created_chunks),
            self.embedding_client.model_name,
        )

        return {
            "document_id": str(document_id),
            "chunks_created": len(created_chunks),
            "status": "success",
        }

    async def reindex_all(self) -> list[dict]:
        """Reindex all documents in the knowledge base.

        Returns:
            List of reindex result dicts.
        """
        documents = await self.repo.list_documents()
        results = []

        for doc in documents:
            try:
                result = await self.reindex_document(doc.id)
                results.append(result)
            except Exception as e:
                logger.error("Failed to reindex document %s: %s", doc.id, e)
                results.append(
                    {
                        "document_id": str(doc.id),
                        "chunks_created": 0,
                        "status": "error",
                        "reason": str(e),
                    }
                )

        return results

    async def reindex_stale(self) -> list[dict]:
        """Reindex documents that have a different embedding model than the current one.

        Returns:
            List of reindex result dicts.
        """
        docs_with_models = await self.repo.list_all_documents_with_embedding_model()
        current_model = self.embedding_client.model_name
        results = []

        for doc_info in docs_with_models:
            if doc_info["embedding_model"] != current_model:
                try:
                    result = await self.reindex_document(doc_info["id"])
                    results.append(result)
                except Exception as e:
                    logger.error(
                        "Failed to reindex stale document %s: %s",
                        doc_info["id"],
                        e,
                    )
                    results.append(
                        {
                            "document_id": str(doc_info["id"]),
                            "chunks_created": 0,
                            "status": "error",
                            "reason": str(e),
                        }
                    )

        return results
