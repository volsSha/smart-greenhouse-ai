"""Main application layout with sidebar navigation.

Provides the shared shell used by all NiceGUI pages: a header bar
and a sidebar with grouped navigation links.
"""

from nicegui import ui

from app.i18n.core import _
from app.ui.components.language_switcher import language_switcher


def main_layout() -> None:
    """Render the main application layout shell.

    Call this at the start of every page to wrap content in the
    standard header + sidebar structure.
    """
    # --- Header ---
    with ui.header():
        ui.label(_("Smart Greenhouse Fleet")).classes("text-lg font-bold")
        ui.space()
        ui.label(_("Fleet Control System")).classes("text-sm opacity-70")
        language_switcher()

    # --- Sidebar ---
    with ui.left_drawer().classes("p-4"):
        ui.label(_("Menu")).classes("text-md font-bold mb-4")

        # Operations group
        ui.label(_("Operations")).classes("text-xs uppercase opacity-50 mt-4 mb-1")
        ui.link(_("Dashboard"), "/dashboard")
        ui.link(_("Simulator"), "/simulator")
        ui.link(_("Plants"), "/plants")
        ui.link(_("Control"), "/control")

        # Intelligence group
        ui.label(_("Intelligence")).classes("text-xs uppercase opacity-50 mt-4 mb-1")
        ui.link(_("AI Chat"), "/ai-chat")
        ui.link(_("RAG"), "/rag")
        ui.link(_("Logs"), "/logs")

        # System group
        ui.label(_("System")).classes("text-xs uppercase opacity-50 mt-4 mb-1")
        ui.link(_("Settings"), "/settings")
