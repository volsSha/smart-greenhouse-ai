"""Control page -- actuator command proposal and approval interface."""

from nicegui import ui

from app.ui.layouts.main_layout import main_layout


@ui.page("/control")
async def control() -> None:
    """Render the actuator control page.

    Placeholder layout for U9. Full implementation will include:
    - Command proposal form (actuator, action, value, duration, reason)
    - Pending commands list with approve/cancel actions
    - Recent commands history
    """
    main_layout()

    ui.label("Actuator Control").classes("text-2xl font-bold mt-6")
    ui.label(
        "Propose, validate, approve, and execute actuator commands."
    ).classes("text-sm opacity-70 mt-2")

    with ui.card().classes("w-full mt-6"):
        ui.label("Propose Command").classes("text-lg font-semibold")

        with ui.row().classes("w-full gap-4 mt-4"):
            ui.select(
                label="Actuator",
                options=["pump", "fan", "heater", "lamp"],
                value="pump",
            ).classes("w-48")
            ui.select(
                label="Action",
                options=["on", "off", "set_power"],
                value="on",
            ).classes("w-48")
            ui.number(label="Value", value=0).classes("w-32")
            ui.number(label="Duration (s)", value=30).classes("w-32")

        with ui.row().classes("w-full gap-4 mt-4"):
            ui.textarea(label="Reason").classes("w-96")
            ui.button("Propose", color="primary")

    with ui.card().classes("w-full mt-6"):
        ui.label("Pending Commands").classes("text-lg font-semibold")
        ui.label("Commands awaiting approval will appear here.").classes(
            "text-sm opacity-70 mt-2"
        )

    with ui.card().classes("w-full mt-6"):
        ui.label("Recent Commands").classes("text-lg font-semibold")
        ui.label("Recently executed commands will appear here.").classes(
            "text-sm opacity-70 mt-2"
        )

    ui.label("Placeholder -- full control UI will be implemented in a later unit.").classes(
        "text-xs italic mt-4"
    )
