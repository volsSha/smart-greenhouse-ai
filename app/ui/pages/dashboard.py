"""Dashboard page -- fleet overview with placeholder content."""

from nicegui import ui

from app.ui.layouts.main_layout import main_layout


@ui.page("/dashboard")
async def dashboard() -> None:
    """Render the fleet dashboard page."""
    main_layout()
    ui.label("Dashboard").classes("text-2xl font-bold mt-6")
    ui.label("Fleet overview and real-time microclimate data will appear here.").classes(
        "text-sm opacity-70 mt-2"
    )
    ui.label("Placeholder -- U6 will implement the full dashboard.").classes(
        "text-xs italic mt-4"
    )
