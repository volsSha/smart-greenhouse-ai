"""Main application layout with sidebar navigation.

Provides the shared shell used by all NiceGUI pages: a header bar
and a sidebar with grouped navigation links.
"""

from nicegui import ui


def main_layout() -> None:
    """Render the main application layout shell.

    Call this at the start of every page to wrap content in the
    standard header + sidebar structure.
    """
    # --- Header ---
    with ui.header():
        ui.label("Smart Greenhouse Fleet").classes("text-lg font-bold")
        ui.space()
        ui.label("Fleet Control System").classes("text-sm opacity-70")

    # --- Sidebar ---
    with ui.left_drawer().classes("p-4"):
        ui.label("Menu").classes("text-md font-bold mb-4")

        # Operations group
        ui.label("Operations").classes("text-xs uppercase opacity-50 mt-4 mb-1")
        ui.link("Dashboard", "/dashboard")
        ui.link("Simulator", "/simulator")
        ui.link("Plants", "/plants")
        ui.link("Control", "/control")

        # Intelligence group
        ui.label("Intelligence").classes("text-xs uppercase opacity-50 mt-4 mb-1")
        ui.link("AI Chat", "/ai-chat")
        ui.link("RAG", "/rag")
        ui.link("Logs", "/logs")

        # System group
        ui.label("System").classes("text-xs uppercase opacity-50 mt-4 mb-1")
        ui.link("Settings", "/settings")
