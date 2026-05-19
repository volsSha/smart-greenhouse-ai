"""Main application layout with sidebar navigation.

Provides the shared shell used by all NiceGUI pages: a header bar
and a sidebar with grouped navigation links.
"""

from nicegui import ui

from app.i18n.core import _
from app.ui.components.language_switcher import language_switcher


def _nav_groups() -> list[tuple[str, list[tuple[str, str, str, str]]]]:
    return [
        (
            _("Operations"),
            [
                (_("Dashboard"), "dashboard", "/dashboard", "dashboard"),
                (_("Simulator"), "precision_manufacturing", "/simulator", "simulator"),
                (_("Zones"), "view_in_ar", "/zones", "zones"),
                (_("Plants"), "local_florist", "/plants", "plants"),
                (_("Control"), "tune", "/control", "control"),
            ],
        ),
        (
            _("Intelligence"),
            [
                (_("AI Chat"), "smart_toy", "/ai-chat", "ai_chat"),
                (_("RAG"), "travel_explore", "/rag", "rag"),
                (_("Logs"), "fact_check", "/logs", "logs"),
            ],
        ),
        (
            _("System"),
            [(_("Settings"), "settings", "/settings", "settings")],
        ),
    ]


def _nav_link(label: str, icon: str, target: str) -> None:
    with ui.link(target=target).classes("greenhouse-nav-link"):
        ui.icon(icon, size="1.1rem")
        ui.label(label).classes("text-sm font-medium")


def main_layout() -> None:
    """Render the main application layout shell.

    Call this at the start of every page to wrap content in the
    standard header + sidebar structure.
    """
    with ui.header().classes("greenhouse-header px-4 py-2"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("eco", size="1.35rem").classes("greenhouse-brand-mark p-2")
            with ui.column().classes("gap-0"):
                ui.label(_("Smart Greenhouse Management")).classes("text-lg font-bold leading-tight")
                ui.label(_("Greenhouse Control System")).classes("text-xs opacity-65")
        ui.space()
        language_switcher()
        with ui.link(target="/logout").classes("greenhouse-nav-link"):
            ui.icon("logout", size="1.1rem")
            ui.label(_("Logout")).classes("text-sm font-medium")

    with ui.left_drawer().classes("greenhouse-drawer p-4"):
        with ui.column().classes("gap-1 mb-5"):
            ui.label(_("Greenhouse Ops")).classes("text-md font-bold")
            ui.label(_("Telemetry, control, and AI guidance")).classes("text-xs opacity-55")

        for group_label, items in _nav_groups():
            ui.label(group_label).classes("text-xs uppercase tracking-widest opacity-45 mt-4 mb-1")
            with ui.column().classes("w-full gap-1"):
                for label, icon, target, _name in items:
                    _nav_link(label, icon, target)
