"""Tests for OpenRouter model catalog client."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.services.openrouter_models import (
    OpenRouterModelCatalogError,
    OpenRouterModelsClient,
)


class TestOpenRouterModelsClient:
    """Tests for OpenRouterModelsClient."""

    @pytest.fixture
    def mock_api_response(self) -> dict:
        """Mock OpenRouter API response with realistic model data."""
        return {
            "data": [
                {
                    "id": "anthropic/claude-3.5-sonnet",
                    "name": "Anthropic: Claude 3.5 Sonnet",
                    "context_length": 200000,
                    "architecture": {
                        "modality": "text+image->text",
                        "input_modalities": ["text", "image"],
                        "output_modalities": ["text"],
                    },
                    "pricing": {
                        "prompt": "3.00e-07",
                        "completion": "1.50e-06",
                    },
                    "top_provider": {
                        "context_length": 200000,
                        "max_completion_tokens": 8192,
                    },
                },
                {
                    "id": "openai/gpt-4o",
                    "name": "OpenAI: GPT-4o",
                    "context_length": 128000,
                    "architecture": {
                        "modality": "text+audio->text",
                        "input_modalities": ["text", "audio"],
                        "output_modalities": ["text"],
                    },
                    "pricing": {
                        "prompt": "2.50e-06",
                        "completion": "1.00e-05",
                    },
                    "top_provider": {
                        "context_length": 128000,
                        "max_completion_tokens": 4096,
                    },
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_fetch_models_success(self, mock_api_response: dict) -> None:
        """fetch_models returns normalized model list on successful API call."""
        client = OpenRouterModelsClient()

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=mock_api_response)
        mock_response.raise_for_status = lambda: None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await client.fetch_models()

        assert len(result) == 2

        # Verify first model normalization
        assert result[0]["model_id"] == "anthropic/claude-3.5-sonnet"
        assert result[0]["name"] == "Anthropic: Claude 3.5 Sonnet"
        assert result[0]["provider"] == "anthropic"
        assert result[0]["prompt_price_per_million"] == 0.3
        assert result[0]["completion_price_per_million"] == 1.5
        assert result[0]["context_length"] == 200000
        assert result[0]["max_completion_tokens"] == 8192
        assert result[0]["capabilities"]["input_text"] is True
        assert result[0]["capabilities"]["input_image"] is True
        assert result[0]["capabilities"]["output_text"] is True

        # Verify second model normalization
        assert result[1]["model_id"] == "openai/gpt-4o"
        assert result[1]["provider"] == "openai"
        assert result[1]["prompt_price_per_million"] == 2.5
        assert result[1]["completion_price_per_million"] == 10.0

    @pytest.mark.asyncio
    async def test_fetch_models_http_error(self) -> None:
        """fetch_models raises OpenRouterModelCatalogError on HTTP error."""
        client = OpenRouterModelsClient()

        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        error = httpx.HTTPStatusError(
            "Server error", request=AsyncMock(), response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(side_effect=error)
            mock_client_class.return_value = mock_client

            with pytest.raises(OpenRouterModelCatalogError) as exc_info:
                await client.fetch_models()

        assert "500" in str(exc_info.value)
        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_models_request_error(self) -> None:
        """fetch_models raises OpenRouterModelCatalogError on network error."""
        client = OpenRouterModelsClient()

        error = httpx.RequestError("Connection failed", request=AsyncMock())

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(side_effect=error)
            mock_client_class.return_value = mock_client

            with pytest.raises(OpenRouterModelCatalogError) as exc_info:
                await client.fetch_models()

        assert "Connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_models_invalid_response_not_dict(self) -> None:
        """fetch_models raises error when API response is not a dict."""
        client = OpenRouterModelsClient()

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=[])

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with pytest.raises(OpenRouterModelCatalogError) as exc_info:
                await client.fetch_models()

        assert "not a dict" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_models_invalid_response_missing_data(self) -> None:
        """fetch_models raises error when response missing 'data' key."""
        client = OpenRouterModelsClient()

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={})

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with pytest.raises(OpenRouterModelCatalogError) as exc_info:
                await client.fetch_models()

        assert "missing 'data' key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_models_invalid_response_data_not_list(self) -> None:
        """fetch_models raises error when 'data' is not a list."""
        client = OpenRouterModelsClient()

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"data": "not-a-list"})

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with pytest.raises(OpenRouterModelCatalogError) as exc_info:
                await client.fetch_models()

        assert "not a list" in str(exc_info.value)

    def test_normalize_model_extracts_provider(self) -> None:
        """_normalize_model extracts provider from model_id."""
        client = OpenRouterModelsClient()

        model = {"id": "anthropic/claude-3", "name": "Claude 3"}
        result = client._normalize_model(model)

        assert result["provider"] == "anthropic"

    def test_normalize_model_no_slash_in_id(self) -> None:
        """_normalize_model returns None provider when no slash in model_id."""
        client = OpenRouterModelsClient()

        model = {"id": "local-model", "name": "Local Model"}
        result = client._normalize_model(model)

        assert result["provider"] is None

    def test_normalize_model_price_conversion(self) -> None:
        """_normalize_model converts per-token prices to per-million."""
        client = OpenRouterModelsClient()

        model = {
            "id": "test/model",
            "name": "Test Model",
            "pricing": {"prompt": "1.23e-06", "completion": "4.56e-06"},
        }
        result = client._normalize_model(model)

        assert result["prompt_price_per_million"] == 1.23
        assert result["completion_price_per_million"] == 4.56

    def test_normalize_model_invalid_price_ignored(self) -> None:
        """_normalize_model keeps None price when parsing fails."""
        client = OpenRouterModelsClient()

        model = {
            "id": "test/model",
            "name": "Test Model",
            "pricing": {"prompt": "invalid", "completion": "1.00e-06"},
        }
        result = client._normalize_model(model)

        assert result["prompt_price_per_million"] is None
        assert result["completion_price_per_million"] == 1.0

    def test_normalize_model_context_length_from_top_provider(self) -> None:
        """_normalize_model uses context_length from top_provider."""
        client = OpenRouterModelsClient()

        model = {
            "id": "test/model",
            "name": "Test Model",
            "context_length": 100000,
            "top_provider": {"context_length": 200000},
        }
        result = client._normalize_model(model)

        assert result["context_length"] == 200000

    def test_normalize_model_fallback_context_length(self) -> None:
        """_normalize_model falls back to root context_length."""
        client = OpenRouterModelsClient()

        model = {
            "id": "test/model",
            "name": "Test Model",
            "context_length": 100000,
            "top_provider": {},
        }
        result = client._normalize_model(model)

        assert result["context_length"] == 100000

    def test_normalize_model_max_completion_tokens(self) -> None:
        """_normalize_model extracts max_completion_tokens from top_provider."""
        client = OpenRouterModelsClient()

        model = {
            "id": "test/model",
            "name": "Test Model",
            "top_provider": {"max_completion_tokens": 4096},
        }
        result = client._normalize_model(model)

        assert result["max_completion_tokens"] == 4096

    def test_normalize_model_builds_capabilities(self) -> None:
        """_normalize_model builds capabilities from architecture."""
        client = OpenRouterModelsClient()

        model = {
            "id": "test/model",
            "name": "Test Model",
            "architecture": {
                "input_modalities": ["text", "image"],
                "output_modalities": ["text"],
            },
            "supported_parameters": ["temperature", "top_p"],
        }
        result = client._normalize_model(model)

        assert result["capabilities"]["input_text"] is True
        assert result["capabilities"]["input_image"] is True
        assert result["capabilities"]["output_text"] is True
        assert result["capabilities"]["param_temperature"] is True
        assert result["capabilities"]["param_top_p"] is True

    def test_normalize_model_preserves_raw_metadata(self) -> None:
        """_normalize_model preserves raw API response in raw_metadata."""
        client = OpenRouterModelsClient()

        model = {
            "id": "test/model",
            "name": "Test Model",
            "custom_field": "custom_value",
        }
        result = client._normalize_model(model)

        assert result["raw_metadata"] == model
