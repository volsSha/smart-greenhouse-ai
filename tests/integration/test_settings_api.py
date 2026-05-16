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
        "control_mode": "mqtt",
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
async def test_update_control_mode_bootstraps_and_persists_without_model_catalog() -> None:
    global _mock_session
    _mock_session = _make_mock_session()
    settings_test_app.dependency_overrides[get_db_session] = _session_override

    with patch("app.api.settings.ModelSettingsRepository") as MockRepo:
        repo = MockRepo.return_value
        repo.bootstrap_settings = AsyncMock(return_value=_settings())
        repo.set_control_mode = AsyncMock(return_value=_settings(control_mode="simulator"))

        transport = ASGITransport(app=settings_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put("/api/settings/control-mode", json={"control_mode": "simulator"})

    settings_test_app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["control_mode"] == "simulator"
    repo.bootstrap_settings.assert_awaited_once()
    repo.set_control_mode.assert_awaited_once_with("simulator")
    repo.get_catalog_model.assert_not_called()
    _mock_session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_update_control_mode_to_mqtt_stops_simulator() -> None:
    global _mock_session
    _mock_session = _make_mock_session()
    settings_test_app.dependency_overrides[get_db_session] = _session_override

    with (
        patch("app.api.settings.ModelSettingsRepository") as MockRepo,
        patch("app.api.settings.stop_simulator_task", new_callable=AsyncMock) as stop_simulator,
    ):
        repo = MockRepo.return_value
        repo.bootstrap_settings = AsyncMock(return_value=_settings(control_mode="simulator"))
        repo.set_control_mode = AsyncMock(return_value=_settings(control_mode="mqtt"))

        transport = ASGITransport(app=settings_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put("/api/settings/control-mode", json={"control_mode": "mqtt"})

    settings_test_app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["control_mode"] == "mqtt"
    stop_simulator.assert_awaited_once_with(settings_test_app.state)


@pytest.mark.anyio
async def test_update_control_mode_to_simulator_does_not_stop_simulator() -> None:
    global _mock_session
    _mock_session = _make_mock_session()
    settings_test_app.dependency_overrides[get_db_session] = _session_override

    with (
        patch("app.api.settings.ModelSettingsRepository") as MockRepo,
        patch("app.api.settings.stop_simulator_task", new_callable=AsyncMock) as stop_simulator,
    ):
        repo = MockRepo.return_value
        repo.bootstrap_settings = AsyncMock(return_value=_settings())
        repo.set_control_mode = AsyncMock(return_value=_settings(control_mode="simulator"))

        transport = ASGITransport(app=settings_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put("/api/settings/control-mode", json={"control_mode": "simulator"})

    settings_test_app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["control_mode"] == "simulator"
    stop_simulator.assert_not_awaited()


@pytest.mark.anyio
async def test_update_control_mode_rejects_invalid_values() -> None:
    global _mock_session
    _mock_session = _make_mock_session()
    settings_test_app.dependency_overrides[get_db_session] = _session_override

    with patch("app.api.settings.ModelSettingsRepository") as MockRepo:
        transport = ASGITransport(app=settings_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put("/api/settings/control-mode", json={"control_mode": "demo"})

    settings_test_app.dependency_overrides.clear()

    assert response.status_code == 422
    MockRepo.assert_not_called()
    _mock_session.commit.assert_not_awaited()


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
