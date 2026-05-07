"""Unit tests for the RAG search AI tool."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_agent.tools.deps import ToolDeps
from app.services.ai_agent.tools.rag_tools import search_plant_knowledge


def _make_tool_deps(
    rag_repo: AsyncMock | None = None,
    settings: object | None = None,
) -> ToolDeps:
    """Create a ToolDeps instance with mocked repositories."""
    deps = ToolDeps(
        group_repo=MagicMock(),
        greenhouse_repo=MagicMock(),
        zone_repo=MagicMock(),
        alert_repo=MagicMock(),
        command_repo=MagicMock(),
        plant_batch_repo=MagicMock(),
        plant_profile_repo=MagicMock(),
        telemetry_repo=MagicMock(),
        sensor_repo=MagicMock(),
        actuator_repo=MagicMock(),
        tool_logger=MagicMock(),
        rag_repo=rag_repo,
        settings=settings,
    )
    return deps


def _make_mock_settings() -> SimpleNamespace:
    """Create a mock Settings object."""
    return SimpleNamespace(
        openrouter=SimpleNamespace(
            api_key="test-api-key",
            base_url="https://openrouter.ai/api/v1",
        )
    )


class TestSearchPlantKnowledge:
    """Tests for search_plant_knowledge tool."""

    @pytest.mark.asyncio
    async def test_search_returns_results(self) -> None:
        """Search should return results when knowledge base has matching content."""
        mock_rag_repo = AsyncMock()
        mock_rag_repo.search.return_value = [
            {
                "content": "Tomatoes need 1-2 inches of water per week.",
                "document_title": "Tomato Care Guide",
                "score": 0.12,
                "metadata": None,
            },
            {
                "content": "Consistent watering prevents blossom end rot.",
                "document_title": "Tomato Care Guide",
                "score": 0.25,
                "metadata": None,
            },
        ]

        mock_settings = _make_mock_settings()
        deps = _make_tool_deps(rag_repo=mock_rag_repo, settings=mock_settings)

        # Mock RunContext
        mock_ctx = SimpleNamespace(deps=deps)

        fake_embedding = [0.1] * 1536

        with patch(
            "app.services.ai_agent.tools.rag_tools.EmbeddingClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.embed.return_value = [fake_embedding]
            mock_client_class.return_value = mock_client

            results = await search_plant_knowledge(
                mock_ctx, query="tomato watering"
            )

        assert len(results) == 2
        assert results[0]["document_title"] == "Tomato Care Guide"
        assert results[0]["score"] == 0.12
        assert "water" in results[0]["content"].lower()
        mock_rag_repo.search.assert_called_once_with(
            query_embedding=fake_embedding,
            limit=10,
            group_id=None,
        )

    @pytest.mark.asyncio
    async def test_search_with_group_id(self) -> None:
        """Search should pass group_id to the repository when provided."""
        mock_rag_repo = AsyncMock()
        mock_rag_repo.search.return_value = []

        mock_settings = _make_mock_settings()
        deps = _make_tool_deps(rag_repo=mock_rag_repo, settings=mock_settings)
        mock_ctx = SimpleNamespace(deps=deps)

        group_id = str(uuid.uuid4())
        fake_embedding = [0.1] * 1536

        with patch(
            "app.services.ai_agent.tools.rag_tools.EmbeddingClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.embed.return_value = [fake_embedding]
            mock_client_class.return_value = mock_client

            results = await search_plant_knowledge(
                mock_ctx, query="pest control", group_id=group_id
            )

        assert results == []
        mock_rag_repo.search.assert_called_once()
        call_kwargs = mock_rag_repo.search.call_args
        assert call_kwargs.kwargs["group_id"] == uuid.UUID(group_id)

    @pytest.mark.asyncio
    async def test_search_empty_knowledge_base(self) -> None:
        """Search should return empty list when knowledge base has no content."""
        mock_rag_repo = AsyncMock()
        mock_rag_repo.search.return_value = []

        mock_settings = _make_mock_settings()
        deps = _make_tool_deps(rag_repo=mock_rag_repo, settings=mock_settings)
        mock_ctx = SimpleNamespace(deps=deps)

        fake_embedding = [0.1] * 1536

        with patch(
            "app.services.ai_agent.tools.rag_tools.EmbeddingClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.embed.return_value = [fake_embedding]
            mock_client_class.return_value = mock_client

            results = await search_plant_knowledge(
                mock_ctx, query="anything"
            )

        assert results == []

    @pytest.mark.asyncio
    async def test_search_without_settings(self) -> None:
        """Search should work even when settings are not provided (defaults)."""
        mock_rag_repo = AsyncMock()
        mock_rag_repo.search.return_value = []

        deps = _make_tool_deps(rag_repo=mock_rag_repo, settings=None)
        mock_ctx = SimpleNamespace(deps=deps)

        fake_embedding = [0.1] * 1536

        with patch(
            "app.services.ai_agent.tools.rag_tools.EmbeddingClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.embed.return_value = [fake_embedding]
            mock_client_class.return_value = mock_client

            results = await search_plant_knowledge(
                mock_ctx, query="test query"
            )

        assert results == []
        # Should create EmbeddingClient with empty api_key and default base_url
        mock_client_class.assert_called_once_with(
            api_key="",
            base_url="https://openrouter.ai/api/v1",
        )
