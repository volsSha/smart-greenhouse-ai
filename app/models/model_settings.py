"""Application settings and OpenRouter model catalog models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdTimestampMixin


class ModelSettings(Base, IdTimestampMixin):
    """Singleton application settings for AI model configuration.

    Tracks the globally selected chat model, configured embedding model,
    refresh status, and metadata. This table should have exactly one row.
    """

    __tablename__ = "model_settings"

    # Selected chat model (saved from admin settings)
    selected_chat_model: Mapped[str | None] = mapped_column(String(200))

    # Embedding model (configured from environment, displayed read-only)
    embedding_model: Mapped[str | None] = mapped_column(String(200))

    # Embedding vector dimension
    embedding_dimension: Mapped[int | None] = mapped_column(Integer)

    # Catalog refresh state
    last_refresh_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    last_refresh_error: Mapped[str | None] = mapped_column(Text)
    last_refresh_status: Mapped[str | None] = mapped_column(String(50))  # 'success', 'failed'

    # Selected model availability flag (derived from catalog presence)
    selected_model_available: Mapped[bool | None] = mapped_column(
        Boolean,
        default=True,
    )

    # Project-wide actuator command execution mode: mqtt | simulator
    control_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="mqtt")


class OpenRouterModelCatalog(Base, IdTimestampMixin):
    """Cached OpenRouter model catalog for admin selection.

    Stores normalized fields for search/filtering and raw metadata for
    flexibility. Refreshed manually by admin action.
    """

    __tablename__ = "openrouter_model_catalog"

    # Identity (normalized)
    model_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)

    # Display fields (normalized)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Provider (normalized)
    provider: Mapped[str | None] = mapped_column(String(100))

    # Capabilities (normalized)
    capabilities: Mapped[dict | None] = mapped_column(
        "capability_flags",
        JSONB,
    )

    # Pricing (normalized, per million tokens)
    prompt_price_per_million: Mapped[float | None] = mapped_column(
        "prompt_price",
        Integer,
    )
    completion_price_per_million: Mapped[float | None] = mapped_column(
        "completion_price",
        Integer,
    )

    # Context window
    context_length: Mapped[int | None] = mapped_column(Integer)

    # Max output tokens
    max_completion_tokens: Mapped[int | None] = mapped_column(Integer)

    # Raw OpenRouter metadata (preserved for future use)
    raw_metadata: Mapped[dict | None] = mapped_column(
        "raw_metadata",
        JSONB,
    )
