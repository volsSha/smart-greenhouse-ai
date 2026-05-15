"""REST endpoints for model settings and OpenRouter catalog management."""

from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings as get_app_settings
from app.dependencies import get_db_session
from app.repositories.model_settings_repository import ModelSettingsRepository
from app.schemas.settings import (
    CatalogModelResponse,
    CatalogRefreshResponse,
    ControlModeUpdateRequest,
    SettingsResponse,
    SettingsUpdateRequest,
)
from app.services.openrouter_models import (
    OpenRouterModelCatalogError,
    OpenRouterModelsClient,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings(
    session: AsyncSession = Depends(get_db_session),
) -> SettingsResponse:
    """Get the current application settings.

    Returns the selected chat model, embedding model configuration,
    and catalog refresh status.
    """
    repo = ModelSettingsRepository(session)

    # Bootstrap settings if they don't exist
    app_settings = get_app_settings()
    settings = await repo.bootstrap_settings(
        embedding_model=app_settings.openrouter.embedding_model,
        embedding_dimension=app_settings.openrouter.embedding_dimension,
    )
    await session.commit()

    return SettingsResponse.model_validate(settings)


@router.put("", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SettingsResponse:
    """Update the selected chat model.

    The model must exist in the current OpenRouter catalog.
    """
    repo = ModelSettingsRepository(session)

    # Verify the model exists in catalog
    catalog_model = await repo.get_catalog_model(body.selected_chat_model)
    if catalog_model is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{body.selected_chat_model}' not found in catalog. Refresh catalog first.",
        )

    # Update the selected model
    settings = await repo.set_selected_chat_model(body.selected_chat_model)
    await session.commit()

    return SettingsResponse.model_validate(settings)


@router.put("/control-mode", response_model=SettingsResponse)
async def update_control_mode(
    body: ControlModeUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SettingsResponse:
    """Update the project-wide actuator execution mode."""
    repo = ModelSettingsRepository(session)
    await repo.bootstrap_settings(
        embedding_model=get_app_settings().openrouter.embedding_model,
        embedding_dimension=get_app_settings().openrouter.embedding_dimension,
    )
    settings = await repo.set_control_mode(body.control_mode)
    await session.commit()
    return SettingsResponse.model_validate(settings)


@router.get("/catalog", response_model=list[CatalogModelResponse])
async def list_catalog(
    search: str | None = None,
    provider: str | None = None,
    capability: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[CatalogModelResponse]:
    """List all models in the OpenRouter catalog with optional filters.

    Args:
        search: Filter by model name or ID (substring match)
        provider: Filter by provider (e.g., "anthropic", "openai")
        capability: Filter by capability flag (e.g., "input_text", "output_text")
    """
    repo = ModelSettingsRepository(session)

    models = await repo.list_catalog(
        search=search,
        provider=provider,
        capability=capability,
    )

    return [CatalogModelResponse.model_validate(m) for m in models]


@router.post("/catalog/refresh", response_model=CatalogRefreshResponse)
async def refresh_catalog(
    session: AsyncSession = Depends(get_db_session),
) -> CatalogRefreshResponse:
    """Refresh the OpenRouter model catalog from the public API.

    Fetches the latest models from OpenRouter and replaces the local catalog.
    Updates the refresh status and selected model availability flag.
    """
    repo = ModelSettingsRepository(session)

    # Fetch from OpenRouter
    client = OpenRouterModelsClient()

    try:
        await repo.bootstrap_settings(
            embedding_model=get_app_settings().openrouter.embedding_model,
            embedding_dimension=get_app_settings().openrouter.embedding_dimension,
        )
        catalog_data = await client.fetch_models()
        catalog_models = await repo.record_refresh_success(catalog_data)
        await session.commit()

        return CatalogRefreshResponse(
            status="success",
            models_added=len(catalog_models),
            last_refresh_at=catalog_models[0].created_at if catalog_models else None,
        )
    except OpenRouterModelCatalogError as e:
        # Record failure but don't delete existing catalog
        await repo.record_refresh_failure(str(e))
        await session.commit()

        return CatalogRefreshResponse(
            status="failed",
            message=str(e),
            models_added=0,
            last_refresh_at=None,
        )
