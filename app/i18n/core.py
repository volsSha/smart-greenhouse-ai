"""Gettext-backed translation helpers for the NiceGUI UI."""

from __future__ import annotations

import gettext
from functools import lru_cache
from pathlib import Path
from collections.abc import MutableMapping
from typing import Final

from nicegui import app, ui

DEFAULT_LANGUAGE: Final = "en"
SUPPORTED_LANGUAGES: Final = {
    "en": "English",
    "uk": "Українська",
}
_LANGUAGE_STORAGE_KEY: Final = "language"
_LOCALE_DIR: Final = Path(__file__).resolve().parents[2] / "locales"


def normalize_language(language: str | None) -> str:
    if language in SUPPORTED_LANGUAGES:
        return language
    return DEFAULT_LANGUAGE


def _user_storage() -> MutableMapping[str, object]:
    return app.storage.user


def get_current_language() -> str:
    try:
        value = _user_storage().get(_LANGUAGE_STORAGE_KEY)
    except RuntimeError:
        return DEFAULT_LANGUAGE
    return normalize_language(value if isinstance(value, str) else None)


def set_language(language: str) -> None:
    _user_storage()[_LANGUAGE_STORAGE_KEY] = normalize_language(language)


def set_language_and_reload(language: str) -> None:
    set_language(language)
    ui.navigate.reload()


@lru_cache(maxsize=len(SUPPORTED_LANGUAGES))
def get_translation(language: str) -> gettext.NullTranslations:
    return gettext.translation(
        "messages",
        localedir=_LOCALE_DIR,
        languages=[normalize_language(language)],
        fallback=True,
    )


def translate(message: str, **kwargs: object) -> str:
    translated = get_translation(get_current_language()).gettext(message)
    if kwargs:
        return translated.format(**kwargs)
    return translated


def _(message: str, **kwargs: object) -> str:
    return translate(message, **kwargs)
