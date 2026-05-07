"""System-level settings page scope checks."""

from __future__ import annotations

import inspect

from app.ui.pages import settings


def test_settings_page_does_not_expose_secret_inputs_or_safety_editing() -> None:
    source = inspect.getsource(settings.settings_page)
    lowered = source.lower()

    assert "password" not in lowered
    assert "token" not in lowered
    assert "api_key" not in lowered
    assert "safety" not in lowered
    assert "placeholder" in lowered
