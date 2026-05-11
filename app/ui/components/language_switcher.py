"""Language switcher component."""

from __future__ import annotations

from nicegui import ui

from app.i18n.core import _, get_current_language, normalize_language, set_language_and_reload


def _selected_language(value: object) -> str:
    if isinstance(value, str):
        labels = {
            _("Ukrainian"): "uk",
            _("English"): "en",
            "Українська": "uk",
            "Англійська": "en",
        }
        return labels.get(value, normalize_language(value))
    return normalize_language(None)


def language_switcher() -> None:
    current_language = get_current_language()
    language_options = {"uk": _("Ukrainian"), "en": _("English")}
    ui.select(
        list(language_options.values()),
        value=language_options[current_language],
        on_change=lambda event: set_language_and_reload(_selected_language(event.value)),
    ).props("dense outlined options-dense").classes("w-36")
