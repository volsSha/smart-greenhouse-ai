"""Integration tests for the RAG API endpoints.

Tests use FastAPI dependency overrides to inject mock sessions,
avoiding the need for a running database.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.api.rag import router as rag_router


# --- Build a minimal test app with just the RAG router ---
from fastapi import FastAPI

rag_test_app = FastAPI()
rag_test_app.include_router(rag_router)


def _make_fake_document(**overrides) -> SimpleNamespace:
    """Create a lightweight fake RAGDocument for API responses."""
    defaults = {
        "id": uuid.uuid4(),
        "group_id": None,
        "title": "Test Document",
        "source_type": "manual",
        "source_url": None,
        "content": "Some agronomic content.",
        "metadata_": None,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_mock_session() -> MagicMock:
    """Create a mock AsyncSession."""
    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock()
    session.delete = AsyncMock()
    session.refresh = AsyncMock()
    session.close = AsyncMock()
    return session


def _make_create_payload(**overrides) -> dict:
    """Create a JSON payload for the create document endpoint."""
    defaults = {
        "title": "Tomato Care Guide",
        "content": "Tomatoes need consistent watering and warm temperatures.",
        "source_type": "manual",
    }
    defaults.update(overrides)
    return defaults


class TestCreateDocumentEndpoint:
    """Tests for POST /api/rag/documents."""

    @pytest.mark.anyio
    async def test_create_document_returns_201(self) -> None:
        """Creating a document returns 201 with the document data."""
        fake_doc = _make_fake_document(title="Tomato Care Guide")
        mock_session = _make_mock_session()

        async def _session_override():
            yield mock_session

        rag_test_app.dependency_overrides[get_db_session] = _session_override

        fake_embedding = [0.1] * 1536

        with (
            patch(
                "app.api.rag.RAGRepository.create_document",
                new_callable=AsyncMock,
                return_value=fake_doc,
            ),
            patch(
                "app.api.rag.RAGRepository.add_chunks",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.api.rag.chunk_text",
                return_value=["Tomatoes need consistent watering and warm temperatures."],
            ),
            patch(
                "app.api.rag._build_embedding_client",
            ) as mock_build_client,
        ):
            mock_client = AsyncMock()
            mock_client.embed.return_value = [fake_embedding]
            mock_client.model_name = "text-embedding-3-small"
            mock_build_client.return_value = mock_client

            transport = ASGITransport(app=rag_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/rag/documents",
                    json=_make_create_payload(),
                )

        rag_test_app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Tomato Care Guide"

    @pytest.mark.anyio
    async def test_create_document_with_metadata(self) -> None:
        """Creating a document with metadata includes it in the response."""
        fake_doc = _make_fake_document(metadata_={"author": "Farmer Bob"})
        mock_session = _make_mock_session()

        async def _session_override():
            yield mock_session

        rag_test_app.dependency_overrides[get_db_session] = _session_override

        with (
            patch(
                "app.api.rag.RAGRepository.create_document",
                new_callable=AsyncMock,
                return_value=fake_doc,
            ),
            patch(
                "app.api.rag.RAGRepository.add_chunks",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.api.rag.chunk_text",
                return_value=["content"],
            ),
            patch(
                "app.api.rag._build_embedding_client",
            ) as mock_build_client,
        ):
            mock_client = AsyncMock()
            mock_client.embed.return_value = [[0.1] * 1536]
            mock_client.model_name = "text-embedding-3-small"
            mock_build_client.return_value = mock_client

            transport = ASGITransport(app=rag_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/rag/documents",
                    json={
                        "title": "Test",
                        "content": "Content",
                        "metadata": {"author": "Farmer Bob"},
                    },
                )

        rag_test_app.dependency_overrides.clear()

        assert response.status_code == 201


class TestCreateTemplateDocumentsEndpoint:
    """Tests for POST /api/rag/documents/templates/ukrainian-greenhouse."""

    @pytest.mark.anyio
    async def test_create_templates_returns_10_documents(self) -> None:
        fake_docs = [_make_fake_document(title=f"Template {i}", source_type="template") for i in range(10)]
        mock_session = _make_mock_session()

        async def _session_override():
            yield mock_session

        rag_test_app.dependency_overrides[get_db_session] = _session_override

        with (
            patch(
                "app.api.rag.RAGRepository.create_document",
                new_callable=AsyncMock,
                side_effect=fake_docs,
            ) as mock_create,
            patch(
                "app.api.rag.RAGRepository.add_chunks",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.api.rag.chunk_text",
                return_value=["content"],
            ),
            patch(
                "app.api.rag._build_embedding_client",
            ) as mock_build_client,
        ):
            mock_client = AsyncMock()
            mock_client.embed.return_value = [[0.1] * 1536]
            mock_client.model_name = "text-embedding-3-small"
            mock_build_client.return_value = mock_client

            transport = ASGITransport(app=rag_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/api/rag/documents/templates/ukrainian-greenhouse")

        rag_test_app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert data["created"] == 10
        assert len(data["documents"]) == 10
        assert mock_create.await_count == 10
        first_call = mock_create.await_args_list[0].kwargs
        assert first_call["source_type"] == "template"
        assert first_call["metadata_"]["language"] == "uk"
        assert "тепли" in first_call["content"].lower()


class TestListDocumentsEndpoint:
    """Tests for GET /api/rag/documents."""

    @pytest.mark.anyio
    async def test_list_returns_200(self) -> None:
        """Listing documents returns 200 with a list."""
        fake_docs = [_make_fake_document(), _make_fake_document(title="Another Doc")]
        mock_session = _make_mock_session()

        async def _session_override():
            yield mock_session

        rag_test_app.dependency_overrides[get_db_session] = _session_override

        with patch(
            "app.api.rag.RAGRepository.list_documents",
            new_callable=AsyncMock,
            return_value=fake_docs,
        ):
            transport = ASGITransport(app=rag_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/rag/documents")

        rag_test_app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.anyio
    async def test_list_empty_returns_empty_list(self) -> None:
        """Listing with no documents returns empty list."""
        mock_session = _make_mock_session()

        async def _session_override():
            yield mock_session

        rag_test_app.dependency_overrides[get_db_session] = _session_override

        with patch(
            "app.api.rag.RAGRepository.list_documents",
            new_callable=AsyncMock,
            return_value=[],
        ):
            transport = ASGITransport(app=rag_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/rag/documents")

        rag_test_app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data == []


class TestDeleteDocumentEndpoint:
    """Tests for DELETE /api/rag/documents/{id}."""

    @pytest.mark.anyio
    async def test_delete_existing_returns_204(self) -> None:
        """Deleting an existing document returns 204."""
        mock_session = _make_mock_session()

        async def _session_override():
            yield mock_session

        rag_test_app.dependency_overrides[get_db_session] = _session_override

        with patch(
            "app.api.rag.RAGRepository.delete_document",
            new_callable=AsyncMock,
            return_value=True,
        ):
            transport = ASGITransport(app=rag_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete(f"/api/rag/documents/{uuid.uuid4()}")

        rag_test_app.dependency_overrides.clear()

        assert response.status_code == 204

    @pytest.mark.anyio
    async def test_delete_nonexistent_returns_404(self) -> None:
        """Deleting a non-existent document returns 404."""
        mock_session = _make_mock_session()

        async def _session_override():
            yield mock_session

        rag_test_app.dependency_overrides[get_db_session] = _session_override

        with patch(
            "app.api.rag.RAGRepository.delete_document",
            new_callable=AsyncMock,
            return_value=False,
        ):
            transport = ASGITransport(app=rag_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete(f"/api/rag/documents/{uuid.uuid4()}")

        rag_test_app.dependency_overrides.clear()

        assert response.status_code == 404


class TestSearchEndpoint:
    """Tests for GET /api/rag/search."""

    @pytest.mark.anyio
    async def test_search_returns_200(self) -> None:
        """Searching returns 200 with results."""
        mock_session = _make_mock_session()

        async def _session_override():
            yield mock_session

        rag_test_app.dependency_overrides[get_db_session] = _session_override

        fake_results = [
            {
                "content": "Tomatoes need water.",
                "document_title": "Tomato Guide",
                "score": 0.15,
                "metadata": None,
            }
        ]
        fake_embedding = [0.1] * 1536

        with (
            patch(
                "app.api.rag.RAGRepository.search",
                new_callable=AsyncMock,
                return_value=fake_results,
            ),
            patch(
                "app.api.rag._build_embedding_client",
            ) as mock_build_client,
        ):
            mock_client = AsyncMock()
            mock_client.embed.return_value = [fake_embedding]
            mock_build_client.return_value = mock_client

            transport = ASGITransport(app=rag_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/api/rag/search",
                    params={"query": "tomato watering"},
                )

        rag_test_app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["document_title"] == "Tomato Guide"

    @pytest.mark.anyio
    async def test_search_empty_query_returns_400(self) -> None:
        """Searching with empty query returns 400."""
        mock_session = _make_mock_session()

        async def _session_override():
            yield mock_session

        rag_test_app.dependency_overrides[get_db_session] = _session_override

        transport = ASGITransport(app=rag_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/rag/search",
                params={"query": "  "},
            )

        rag_test_app.dependency_overrides.clear()

        assert response.status_code == 400

    @pytest.mark.anyio
    async def test_search_no_results_returns_empty_list(self) -> None:
        """Searching with no matches returns empty list."""
        mock_session = _make_mock_session()

        async def _session_override():
            yield mock_session

        rag_test_app.dependency_overrides[get_db_session] = _session_override

        fake_embedding = [0.1] * 1536

        with (
            patch(
                "app.api.rag.RAGRepository.search",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.api.rag._build_embedding_client",
            ) as mock_build_client,
        ):
            mock_client = AsyncMock()
            mock_client.embed.return_value = [fake_embedding]
            mock_build_client.return_value = mock_client

            transport = ASGITransport(app=rag_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/api/rag/search",
                    params={"query": "nonexistent topic"},
                )

        rag_test_app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data == []


class TestReindexEndpoint:
    """Tests for POST /api/rag/reindex."""

    @pytest.mark.anyio
    async def test_reindex_all_returns_200(self) -> None:
        """Reindexing all documents returns 200."""
        mock_session = _make_mock_session()

        async def _session_override():
            yield mock_session

        rag_test_app.dependency_overrides[get_db_session] = _session_override

        with (
            patch(
                "app.api.rag._build_embedding_client",
            ) as mock_build_client,
            patch(
                "app.api.rag.RAGRepository.list_documents",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            mock_client = AsyncMock()
            mock_build_client.return_value = mock_client

            transport = ASGITransport(app=rag_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/api/rag/reindex")

        rag_test_app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
