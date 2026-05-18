"""Shared HTTP client for server-side NiceGUI API calls."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from nicegui import ui

from app.auth import AUTH_COOKIE_NAME, is_auth_enabled, session_token
from app.config import get_settings


@asynccontextmanager
async def api_client(timeout: float = 10.0) -> AsyncIterator[httpx.AsyncClient]:
    """Yield an HTTP client configured for the local FastAPI API."""
    settings = get_settings()
    cookies = None
    if is_auth_enabled(settings):
        token = ui.context.client.request.cookies.get(AUTH_COOKIE_NAME) or session_token(settings)
        cookies = {AUTH_COOKIE_NAME: token}
    async with httpx.AsyncClient(
        base_url=settings.app.api_base_url,
        timeout=timeout,
        cookies=cookies,
    ) as client:
        yield client


def response_error(response: httpx.Response) -> str:
    """Return a user-facing error string from an HTTP response."""
    try:
        detail = response.json().get("detail")
    except ValueError:
        detail = None
    return str(detail or response.text or response.reason_phrase)
