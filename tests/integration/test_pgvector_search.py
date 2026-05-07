"""Integration tests for pgvector similarity search (mocked database)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.repositories.rag_repository import RAGRepository


def _make_mock_session() -> MagicMock:
    """Create a mock AsyncSession."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


class TestRAGRepositoryVectorSearch:
    """Tests for pgvector cosine similarity search via RAGRepository."""

    @pytest.mark.asyncio
    async def test_search_returns_sorted_results(self) -> None:
        """Search should return results sorted by cosine distance (ascending)."""
        mock_session = _make_mock_session()
        repo = RAGRepository(mock_session)

        # Simulate database rows returned by the search query
        mock_rows = [
            SimpleNamespace(
                content="Tomatoes need consistent watering.",
                document_title="Tomato Care Guide",
                score=0.10,  # Lower distance = more similar
                metadata_=None,
            ),
            SimpleNamespace(
                content="Overwatering causes root rot.",
                document_title="Common Plant Problems",
                score=0.35,  # Higher distance = less similar
                metadata_={"page": 5},
            ),
        ]

        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        mock_session.execute = AsyncMock(return_value=mock_result)

        query_embedding = [0.1] * 1536
        results = await repo.search(query_embedding=query_embedding, limit=10)

        assert len(results) == 2
        assert results[0]["score"] < results[1]["score"]
        assert results[0]["document_title"] == "Tomato Care Guide"
        assert results[1]["metadata"]["page"] == 5

    @pytest.mark.asyncio
    async def test_search_with_group_filter(self) -> None:
        """Search should pass group_id filter to the query."""
        mock_session = _make_mock_session()
        repo = RAGRepository(mock_session)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        group_id = uuid.uuid4()
        query_embedding = [0.1] * 1536
        results = await repo.search(
            query_embedding=query_embedding,
            limit=5,
            group_id=group_id,
        )

        assert results == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_empty_knowledge_base(self) -> None:
        """Search should return empty list when no chunks have embeddings."""
        mock_session = _make_mock_session()
        repo = RAGRepository(mock_session)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        query_embedding = [0.1] * 1536
        results = await repo.search(query_embedding=query_embedding)

        assert results == []


class TestRAGRepositoryDocumentCRUD:
    """Tests for document CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_document(self) -> None:
        """Creating a document should add it to the session and flush."""
        mock_session = _make_mock_session()
        repo = RAGRepository(mock_session)

        fake_doc = SimpleNamespace(
            id=uuid.uuid4(),
            title="Test",
            content="Content",
        )
        mock_session.flush = AsyncMock()
        mock_session.add = MagicMock()

        # We need to mock the actual RAGDocument creation
        with patch("app.repositories.rag_repository.RAGDocument") as mock_model:
            mock_model.return_value = fake_doc
            doc = await repo.create_document(
                title="Test",
                content="Content",
            )

        mock_session.add.assert_called_once_with(fake_doc)
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_document(self) -> None:
        """Getting a document should delegate to session.get."""
        mock_session = _make_mock_session()
        repo = RAGRepository(mock_session)

        fake_doc = SimpleNamespace(id=uuid.uuid4(), title="Test")
        mock_session.get = AsyncMock(return_value=fake_doc)

        doc_id = uuid.uuid4()
        doc = await repo.get_document(doc_id)

        assert doc is fake_doc
        mock_session.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_document_found(self) -> None:
        """Deleting an existing document should return True."""
        mock_session = _make_mock_session()
        repo = RAGRepository(mock_session)

        fake_doc = SimpleNamespace(id=uuid.uuid4())
        mock_session.get = AsyncMock(return_value=fake_doc)
        mock_session.delete = AsyncMock()

        result = await repo.delete_document(fake_doc.id)

        assert result is True
        mock_session.delete.assert_awaited_once_with(fake_doc)

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self) -> None:
        """Deleting a non-existent document should return False."""
        mock_session = _make_mock_session()
        repo = RAGRepository(mock_session)

        mock_session.get = AsyncMock(return_value=None)

        result = await repo.delete_document(uuid.uuid4())

        assert result is False


class TestRAGRepositoryChunkOperations:
    """Tests for chunk add and delete operations."""

    @pytest.mark.asyncio
    async def test_add_chunks(self) -> None:
        """Adding chunks should create RAGChunk instances and flush."""
        mock_session = _make_mock_session()
        repo = RAGRepository(mock_session)

        chunk_data = [
            {
                "chunk_index": 0,
                "content": "First chunk.",
                "embedding": [0.1] * 1536,
                "embedding_model": "text-embedding-3-small",
                "metadata": None,
            },
            {
                "chunk_index": 1,
                "content": "Second chunk.",
                "embedding": [0.2] * 1536,
                "embedding_model": "text-embedding-3-small",
                "metadata": None,
            },
        ]

        with patch("app.repositories.rag_repository.RAGChunk") as mock_chunk_model:
            mock_chunk_model.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)
            chunks = await repo.add_chunks(uuid.uuid4(), chunk_data)

        assert len(chunks) == 2
        assert mock_session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_list_documents_with_embedding_model(self) -> None:
        """Listing documents with embedding model should return correct data."""
        mock_session = _make_mock_session()
        repo = RAGRepository(mock_session)

        doc_id = uuid.uuid4()
        mock_rows = [
            SimpleNamespace(id=doc_id, embedding_model="text-embedding-3-small"),
        ]

        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        mock_session.execute = AsyncMock(return_value=mock_result)

        results = await repo.list_all_documents_with_embedding_model()

        assert len(results) == 1
        assert results[0]["id"] == doc_id
        assert results[0]["embedding_model"] == "text-embedding-3-small"
