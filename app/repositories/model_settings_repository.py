"""Repository for model settings and OpenRouter catalog."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_settings import ModelSettings, OpenRouterModelCatalog


class ModelSettingsRepository:
    """Repository for application settings and OpenRouter model catalog."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- Settings ---

    async def get_settings(self) -> ModelSettings | None:
        """Get the singleton settings record."""
        result = await self.session.execute(select(ModelSettings).limit(1))
        return result.scalar_one_or_none()

    async def bootstrap_settings(
        self,
        *,
        embedding_model: str | None = None,
        embedding_dimension: int | None = None,
    ) -> ModelSettings:
        """Ensure settings record exists; create if missing and return it.

        Updates embedding model/dimension if provided.
        """
        settings = await self.get_settings()
        if settings is None:
            settings = ModelSettings(
                selected_chat_model=None,
                embedding_model=embedding_model,
                embedding_dimension=embedding_dimension,
                selected_model_available=True,
                last_refresh_status="success",
            )
            self.session.add(settings)
            await self.session.flush()
        else:
            if embedding_model is not None:
                settings.embedding_model = embedding_model
            if embedding_dimension is not None:
                settings.embedding_dimension = embedding_dimension
            await self.session.flush()
        return settings

    async def set_selected_chat_model(self, model_id: str) -> ModelSettings:
        """Update the selected chat model."""
        settings = await self.get_settings()
        if settings is None:
            raise RuntimeError("Settings not bootstrapped")
        settings.selected_chat_model = model_id
        settings.selected_model_available = True  # Optimistic; validate separately
        await self.session.flush()
        return settings

    async def update_selected_model_availability(self, available: bool) -> ModelSettings:
        """Update selected model availability flag based on catalog presence."""
        settings = await self.get_settings()
        if settings is None:
            raise RuntimeError("Settings not bootstrapped")
        settings.selected_model_available = available
        await self.session.flush()
        return settings

    # --- Catalog refresh ---

    async def record_refresh_success(
        self,
        catalog_data: list[dict[str, Any]],
    ) -> list[OpenRouterModelCatalog]:
        """Persist successful catalog refresh and update status."""
        settings = await self.get_settings()
        if settings is None:
            raise RuntimeError("Settings not bootstrapped")

        # Clear old catalog and insert new data
        # (In production, consider soft-delete or timestamped versioning)
        for old_row in await self.session.scalars(select(OpenRouterModelCatalog)):
            await self.session.delete(old_row)

        catalog_rows = []
        for item in catalog_data:
            row = OpenRouterModelCatalog(
                model_id=item["model_id"],
                name=item["name"],
                provider=item.get("provider"),
                capabilities=item.get("capabilities"),
                prompt_price_per_million=item.get("prompt_price_per_million"),
                completion_price_per_million=item.get("completion_price_per_million"),
                context_length=item.get("context_length"),
                max_completion_tokens=item.get("max_completion_tokens"),
                raw_metadata=item.get("raw_metadata"),
            )
            self.session.add(row)
            catalog_rows.append(row)

        settings.last_refresh_at = datetime.now(timezone.utc)
        settings.last_refresh_status = "success"
        settings.last_refresh_error = None
        settings.selected_model_available = (
            settings.selected_chat_model is None
            or any(
                row.model_id == settings.selected_chat_model
                for row in catalog_rows
            )
        )
        await self.session.flush()

        return catalog_rows

    async def record_refresh_failure(self, error_message: str) -> ModelSettings:
        """Record refresh failure without deleting existing catalog."""
        settings = await self.get_settings()
        if settings is None:
            raise RuntimeError("Settings not bootstrapped")

        settings.last_refresh_at = datetime.now(timezone.utc)
        settings.last_refresh_status = "failed"
        settings.last_refresh_error = error_message
        await self.session.flush()
        return settings

    # --- Catalog queries ---

    async def list_catalog(
        self,
        *,
        search: str | None = None,
        provider: str | None = None,
        capability: str | None = None,
    ) -> list[OpenRouterModelCatalog]:
        """Query catalog with optional filters."""
        stmt = select(OpenRouterModelCatalog).order_by(
            OpenRouterModelCatalog.provider,
            OpenRouterModelCatalog.name,
        )

        if search:
            stmt = stmt.where(
                (OpenRouterModelCatalog.name.ilike(f"%{search}%"))
                | (OpenRouterModelCatalog.model_id.ilike(f"%{search}%"))
            )

        if provider:
            stmt = stmt.where(OpenRouterModelCatalog.provider == provider)

        if capability:
            # JSONB capability filter: capability_flags @> '{"key": true}'
            stmt = stmt.where(
                OpenRouterModelCatalog.capabilities[capability].astext()
                == "true"
            )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_catalog_model(self, model_id: str) -> OpenRouterModelCatalog | None:
        """Get a specific catalog model by ID."""
        return await self.session.get(OpenRouterModelCatalog, model_id)
