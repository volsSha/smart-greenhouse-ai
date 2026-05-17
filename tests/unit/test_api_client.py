"""Tests for shared UI API client helpers."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from app.auth import AUTH_COOKIE_NAME
from app.ui import api_client as api_client_module
from app.ui.api_client import api_client, response_error


@pytest.mark.asyncio
async def test_api_client_forwards_browser_session_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(api_client_module.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(
        api_client_module.ui,
        "context",
        SimpleNamespace(client=SimpleNamespace(request=SimpleNamespace(cookies={AUTH_COOKIE_NAME: "browser-token"}))),
    )
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", "configured")
    monkeypatch.setenv("APP_SECRET", "secret")
    monkeypatch.setenv("API_BASE_URL", "https://greenhouse.example.test")

    async with api_client():
        pass

    assert captured["base_url"] == "https://greenhouse.example.test"
    assert captured["cookies"] == {AUTH_COOKIE_NAME: "browser-token"}


def test_response_error_extracts_json_detail() -> None:
    response = httpx.Response(400, json={"detail": "Bad catalog"})

    assert response_error(response) == "Bad catalog"


def test_response_error_falls_back_to_text() -> None:
    response = httpx.Response(500, text="Internal Server Error")

    assert response_error(response) == "Internal Server Error"
