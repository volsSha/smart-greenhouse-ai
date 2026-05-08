"""OpenRouter model catalog client and normalization."""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OpenRouterModelCatalogError(Exception):
    """Raised when the OpenRouter model catalog API fails."""


class OpenRouterModelsClient:
    """Client for fetching and normalizing OpenRouter model metadata.

    Uses the public GET /api/v1/models endpoint; no API key is required.
    """

    BASE_URL = "https://openrouter.ai/api/v1"

    async def fetch_models(self) -> list[dict[str, Any]]:
        """Fetch all models from OpenRouter and normalize for storage.

        Returns:
            List of normalized model dicts with keys:
            - model_id (str)
            - name (str)
            - provider (str | None)
            - capabilities (dict | None)
            - prompt_price_per_million (float | None)
            - completion_price_per_million (float | None)
            - context_length (int | None)
            - max_completion_tokens (int | None)
            - raw_metadata (dict)

        Raises:
            OpenRouterModelCatalogError: if the API call fails or response is invalid.
        """
        url = f"{self.BASE_URL}/models"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error("OpenRouter catalog HTTP error: %s %s", e.response.status_code, e.response.text)
            raise OpenRouterModelCatalogError(
                f"OpenRouter catalog returned {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            logger.error("OpenRouter catalog request failed: %s", e)
            raise OpenRouterModelCatalogError(f"OpenRouter catalog request failed: {e}") from e

        # Validate response structure
        if not isinstance(data, dict):
            raise OpenRouterModelCatalogError("OpenRouter catalog response is not a dict")

        if "data" not in data:
            raise OpenRouterModelCatalogError("OpenRouter catalog response missing 'data' key")

        models_data = data["data"]
        if not isinstance(models_data, list):
            raise OpenRouterModelCatalogError("OpenRouter catalog 'data' is not a list")

        # Normalize each model
        normalized = []
        for model in models_data:
            normalized.append(self._normalize_model(model))
        return normalized

    def _normalize_model(self, model: dict[str, Any]) -> dict[str, Any]:
        """Normalize a single model from OpenRouter catalog format."""
        model_id = model.get("id", "")
        name = model.get("name", "")

        # Extract provider from model_id (e.g., "anthropic/claude-3" -> "anthropic")
        provider = None
        if "/" in model_id:
            provider = model_id.split("/", 1)[0]

        # Normalize pricing from per-token to per-million
        prompt_price_per_million = None
        completion_price_per_million = None

        pricing = model.get("pricing", {})
        if isinstance(pricing, dict):
            prompt_price = pricing.get("prompt")
            completion_price = pricing.get("completion")

            if prompt_price is not None:
                try:
                    # Parse string decimal and convert to per-million
                    prompt_per_token = Decimal(str(prompt_price))
                    prompt_price_per_million = float(prompt_per_token * 1_000_000)
                except (ValueError, TypeError, InvalidOperation):
                    pass  # Keep None if parsing fails

            if completion_price is not None:
                try:
                    completion_per_token = Decimal(str(completion_price))
                    completion_price_per_million = float(
                        completion_per_token * 1_000_000
                    )
                except (ValueError, TypeError, InvalidOperation):
                    pass

        # Context length from top_provider if present
        context_length = model.get("context_length")
        top_provider = model.get("top_provider", {})
        if isinstance(top_provider, dict):
            context_length = top_provider.get("context_length") or context_length

        max_completion_tokens = None
        if isinstance(top_provider, dict):
            max_completion_tokens = top_provider.get("max_completion_tokens")

        # Build capabilities dict for filtering
        capabilities = {}
        architecture = model.get("architecture", {})

        # Input modalities
        input_modalities = architecture.get("input_modalities", [])
        if isinstance(input_modalities, list):
            for modality in input_modalities:
                if isinstance(modality, str):
                    capabilities[f"input_{modality}"] = True

        # Output modalities
        output_modalities = architecture.get("output_modalities", [])
        if isinstance(output_modalities, list):
            for modality in output_modalities:
                if isinstance(modality, str):
                    capabilities[f"output_{modality}"] = True

        # Supported parameters
        supported = model.get("supported_parameters", [])
        if isinstance(supported, list):
            for param in supported:
                if isinstance(param, str):
                    capabilities[f"param_{param}"] = True

        # Raw metadata preserved for future use
        raw_metadata = model

        return {
            "model_id": model_id,
            "name": name,
            "provider": provider,
            "capabilities": capabilities if capabilities else None,
            "prompt_price_per_million": prompt_price_per_million,
            "completion_price_per_million": completion_price_per_million,
            "context_length": context_length,
            "max_completion_tokens": max_completion_tokens,
            "raw_metadata": raw_metadata,
        }
