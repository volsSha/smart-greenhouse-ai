"""Language switcher component."""

from __future__ import annotations

from nicegui import ui

from app.i18n.core import _, get_current_language, set_language_and_reload


def language_switcher() -> None:
    current_language = get_current_language()

    with ui.row().classes("gap-1 items-center"):
        for language, label in (("uk", "UA"), ("en", "EN")):
            button = ui.button(label, on_click=lambda lang=language: set_language_and_reload(lang)).props("dense size=sm")
            if language == current_language:
                button.props("color=primary")
            else:
                button.props("flat")
            button.tooltip(_("Ukrainian") if language == "uk" else _("English"))
