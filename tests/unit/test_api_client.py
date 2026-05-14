"""Tests for shared UI API client helpers."""

from __future__ import annotations

import httpx

from app.ui.api_client import response_error


def test_response_error_extracts_json_detail() -> None:
    response = httpx.Response(400, json={"detail": "Bad catalog"})

    assert response_error(response) == "Bad catalog"


def test_response_error_falls_back_to_text() -> None:
    response = httpx.Response(500, text="Internal Server Error")

    assert response_error(response) == "Internal Server Error"
