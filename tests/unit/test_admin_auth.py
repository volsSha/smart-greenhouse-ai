"""Tests for app-level admin authentication."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import AUTH_COOKIE_NAME, hash_admin_password, is_public_path, session_token, verify_admin_password
from app.config import AppSettings, DatabaseSettings, InfluxDBSettings, MQTTSettings, OpenRouterSettings, Settings
from app.main import app


def _auth_settings() -> Settings:
    return Settings(
        database=DatabaseSettings(),
        influxdb=InfluxDBSettings(),
        mqtt=MQTTSettings(),
        openrouter=OpenRouterSettings(),
        app=AppSettings(
            app_secret="test-secret",
            admin_username="admin",
            admin_password_hash=hash_admin_password("correct-password", salt="test-salt", iterations=1),
            debug=True,
        ),
    )


@pytest.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    previous_settings = getattr(app.state, "settings", None)
    app.state.settings = _auth_settings()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as ac:
        yield ac

    if previous_settings is None:
        delattr(app.state, "settings")
    else:
        app.state.settings = previous_settings


def test_admin_password_hash_verifies_expected_password() -> None:
    password_hash = hash_admin_password("correct-password", salt="test-salt", iterations=1)

    assert verify_admin_password("correct-password", password_hash)
    assert not verify_admin_password("wrong-password", password_hash)
    assert not verify_admin_password("correct-password", "invalid")


def test_nicegui_internal_paths_stay_public() -> None:
    assert is_public_path("/_nicegui/1.js")
    assert is_public_path("/_nicegui_ws/socket.io/")


@pytest.mark.anyio
async def test_liveness_stays_public(client: AsyncClient) -> None:
    response = await client.get("/api/health/live")

    assert response.status_code == 200


@pytest.mark.anyio
async def test_protected_api_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/debug-logs")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


@pytest.mark.anyio
async def test_protected_page_redirects_to_login(client: AsyncClient) -> None:
    response = await client.get("/dashboard")

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


@pytest.mark.anyio
async def test_login_sets_signed_session_cookie(client: AsyncClient) -> None:
    response = await client.post(
        "/login",
        data={"username": "admin", "password": "correct-password"},
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert client.cookies.get(AUTH_COOKIE_NAME) == session_token(_auth_settings())


@pytest.mark.anyio
async def test_login_rejects_bad_password(client: AsyncClient) -> None:
    response = await client.post(
        "/login",
        data={"username": "admin", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert AUTH_COOKIE_NAME not in client.cookies


@pytest.mark.anyio
async def test_signed_cookie_allows_protected_api_to_reach_route(client: AsyncClient) -> None:
    client.cookies.set(AUTH_COOKIE_NAME, session_token(_auth_settings()))

    response = await client.get("/api/unknown")

    assert response.status_code == 404
