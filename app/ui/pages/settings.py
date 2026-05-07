"""Settings page -- system configuration placeholder."""

from nicegui import ui

from app.ui.layouts.main_layout import main_layout


@ui.page("/settings")
async def settings_page() -> None:
    """Render the system settings page."""
    main_layout()
    ui.label("Settings").classes("text-2xl font-bold mt-6")
    ui.label("System configuration and preferences will appear here.").classes(
        "text-sm opacity-70 mt-2"
    )
    ui.label("Placeholder -- settings UI will be implemented in a future unit.").classes(
        "text-xs italic mt-4"
    )
