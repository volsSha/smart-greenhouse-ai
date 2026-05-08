"""Pydantic v2 schemas for model settings and OpenRouter catalog."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    """Schema for the current application settings."""

    selected_chat_model: str | None = Field(
        None,
        description="Currently selected chat model ID from OpenRouter catalog",
    )
    embedding_model: str | None = Field(
        None,
        description="Embedding model ID (fixed - changing requires RAG reindex)",
    )
    embedding_dimension: int | None = Field(
        None,
        description="Embedding vector dimension",
    )
    last_refresh_at: datetime | None = Field(
        None,
        description="Last successful catalog refresh timestamp",
    )
    last_refresh_error: str | None = Field(
        None,
        description="Error message from last refresh attempt if failed",
    )
    last_refresh_status: str | None = Field(
        None,
        description="Status of last catalog refresh: success or failed",
    )
    selected_model_available: bool = Field(
        ...,
        description="Whether the selected chat model is available in the current catalog",
    )

    model_config = {"from_attributes": True}


class SettingsUpdateRequest(BaseModel):
    """Schema for updating the selected chat model."""

    selected_chat_model: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Model ID to select as the chat model (must exist in catalog)",
    )


class CatalogModelResponse(BaseModel):
    """Schema for a single OpenRouter catalog model."""

    id: UUID
    model_id: str = Field(..., description="OpenRouter model identifier (e.g., 'anthropic/claude-3')")
    name: str = Field(..., description="Human-readable model name")
    provider: str | None = Field(None, description="Model provider (extracted from model_id)")
    capabilities: dict | None = Field(None, description="Model capabilities as JSONB")
    prompt_price_per_million: float | None = Field(None, description="Prompt price per million tokens")
    completion_price_per_million: float | None = Field(None, description="Completion price per million tokens")
    context_length: int | None = Field(None, description="Maximum context window in tokens")
    max_completion_tokens: int | None = Field(None, description="Maximum completion tokens")
    created_at: datetime

    model_config = {"from_attributes": True}


class CatalogRefreshResponse(BaseModel):
    """Schema for catalog refresh operation response."""

    status: str = Field(..., description="Refresh operation status: success or failed")
    message: str | None = Field(None, description="Optional error message if failed")
    models_added: int = Field(..., description="Number of models added to catalog")
    last_refresh_at: datetime | None = Field(None, description="Timestamp of successful refresh")
