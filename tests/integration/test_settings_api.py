"""Integration tests for settings API endpoints."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.settings import router as settings_router
from app.dependencies import get_db_session


settings_test_app = FastAPI()
settings_test_app.include_router(settings_router)

_mock_session: MagicMock | None = None


async def _session_override() -> AsyncGenerator[AsyncSession, None]:
    assert _mock_session is not None
    yield _mock_session  # type: ignore[misc]


def _make_mock_session() -> MagicMock:
    session = MagicMock(spec=AsyncSession)
    session.commit = AsyncMock()
    return session


def _settings(**overrides: object) -> SimpleNamespace:
    defaults = {
        "selected_chat_model": None,
        "embedding_model": "openai/text-embedding-3-small",
        "embedding_dimension": 1536,
        "last_refresh_at": None,
        "last_refresh_error": None,
        "last_refresh_status": "success",
        "selected_model_available": True,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@pytest.mark.anyio
async def test_get_settings_commits_bootstrapped_settings() -> None:
    global _mock_session
    _mock_session = _make_mock_session()
    settings_test_app.dependency_overrides[get_db_session] = _session_override

    with patch("app.api.settings.ModelSettingsRepository") as MockRepo:
        MockRepo.return_value.bootstrap_settings = AsyncMock(return_value=_settings())

        transport = ASGITransport(app=settings_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/settings")

    settings_test_app.dependency_overrides.clear()

    assert response.status_code == 200
    _mock_session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_refresh_catalog_bootstraps_settings_before_recording_success() -> None:
    global _mock_session
    _mock_session = _make_mock_session()
    settings_test_app.dependency_overrides[get_db_session] = _session_override
    created_at = datetime.now(timezone.utc)

    with (
        patch("app.api.settings.ModelSettingsRepository") as MockRepo,
        patch("app.api.settings.OpenRouterModelsClient") as MockClient,
    ):
        repo = MockRepo.return_value
        repo.bootstrap_settings = AsyncMock(return_value=_settings())
        repo.record_refresh_success = AsyncMock(return_value=[SimpleNamespace(created_at=created_at)])
        MockClient.return_value.fetch_models = AsyncMock(return_value=[{"model_id": "test/model"}])

        transport = ASGITransport(app=settings_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/settings/catalog/refresh")

    settings_test_app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    repo.bootstrap_settings.assert_awaited_once()
    repo.record_refresh_success.assert_awaited_once_with([{"model_id": "test/model"}])
    _mock_session.commit.assert_awaited_once()
