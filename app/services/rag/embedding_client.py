"""Embedding client abstraction for RAG.

Uses OpenAI-compatible embedding API (OpenRouter or direct OpenAI).
Tracks embedding model metadata for reindex detection.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_DIMENSION = 1536


class EmbeddingClient:
    """Client for generating embeddings via an OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = DEFAULT_EMBEDDING_MODEL,
        dimension: int = DEFAULT_EMBEDDING_DIMENSION,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimension = dimension

    @property
    def model_name(self) -> str:
        """Return the model identifier used for embeddings."""
        return self.model

    @property
    def model_dimension(self) -> int:
        """Return the embedding vector dimension."""
        return self.dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (each a list of floats).

        Raises:
            EmbeddingError: If the API call fails.
        """
        if not texts:
            return []

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "input": texts,
        }

        # Some providers support dimensions parameter
        if self.model.startswith("text-embedding-3"):
            payload["dimensions"] = self.dimension

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error("Embedding API error: %s %s", e.response.status_code, e.response.text)
            raise EmbeddingError(
                f"Embedding API returned {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            logger.error("Embedding API request failed: %s", e)
            raise EmbeddingError(f"Embedding API request failed: {e}") from e

        # Sort results by index to ensure correct ordering
        results = sorted(data["data"], key=lambda x: x["index"])

        embeddings = [item["embedding"] for item in results]

        # Validate dimensions
        for i, emb in enumerate(embeddings):
            if len(emb) != self.dimension:
                raise EmbeddingError(
                    f"Embedding dimension mismatch: expected {self.dimension}, "
                    f"got {len(emb)} for text index {i}"
                )

        return embeddings


class EmbeddingError(Exception):
    """Raised when the embedding API call fails."""
