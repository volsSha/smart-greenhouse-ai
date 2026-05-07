"""Control page -- actuator command proposal and approval interface."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from nicegui import ui

from app.schemas.commands import CommandPropose
from app.services.command_service import CommandError, CommandService
from app.ui.components.proposed_action_card import proposed_action_card
from app.ui.layouts.main_layout import main_layout

_SAMPLE_GROUP_ID = "00000000-0000-0000-0000-000000000001"
_SAMPLE_GREENHOUSE_ID = "00000000-0000-0000-0000-000000000002"
_SAMPLE_ZONE_ID = "00000000-0000-0000-0000-000000000003"


@ui.page("/control")
async def control() -> None:
    """Render the actuator control page."""
    main_layout()

    ui.label("Actuator Control").classes("text-2xl font-bold mt-6")
    ui.label("Propose, validate, approve, and execute actuator commands.").classes(
        "text-sm opacity-70 mt-2"
    )

    with ui.card().classes("w-full mt-6"):
        ui.label("Propose Command").classes("text-lg font-semibold")
        with ui.row().classes("w-full gap-4 mt-4"):
            group_id = ui.input("Group ID", value=_SAMPLE_GROUP_ID).classes("w-80")
            greenhouse_id = ui.input("Greenhouse ID", value=_SAMPLE_GREENHOUSE_ID).classes("w-80")
            zone_id = ui.input("Zone ID", value=_SAMPLE_ZONE_ID).classes("w-80")
        with ui.row().classes("w-full gap-4 mt-4"):
            actuator = ui.select(
                label="Actuator",
                options=["pump", "fan", "heater", "lamp"],
                value="pump",
            ).classes("w-48")
            action = ui.select(
                label="Action",
                options=["on", "off", "set_power"],
                value="on",
            ).classes("w-48")
            value = ui.number(label="Value", value=None).classes("w-32")
            duration = ui.number(label="Duration (s)", value=30).classes("w-32")
        reason = ui.textarea(label="Reason", value="Manual greenhouse adjustment").classes("w-full mt-4")
        ui.button(
            "Propose",
            color="primary",
            on_click=lambda: ui.notify(
                _proposal_preview(
                    group_id.value,
                    greenhouse_id.value,
                    zone_id.value,
                    actuator.value,
                    action.value,
                    value.value,
                    duration.value,
                    reason.value,
                ),
                type="info",
            ),
        )

    with ui.card().classes("w-full mt-6"):
        ui.label("Pending Commands").classes("text-lg font-semibold")
        ui.label(
            "Validated and AI-generated proposals require approval before MQTT execution."
        ).classes("text-sm opacity-70 mt-2")
        proposed_action_card(
            {
                "command_id": "pending-command-id",
                "group_id": _SAMPLE_GROUP_ID,
                "greenhouse_id": _SAMPLE_GREENHOUSE_ID,
                "zone_id": _SAMPLE_ZONE_ID,
                "actuator": "pump",
                "action": "on",
                "duration_seconds": 30,
                "reason": "Soil moisture below configured threshold.",
                "status": "validated",
            },
            on_approve=lambda command_id: ui.notify(
                f"Approve {command_id} via /api/commands/{{id}}/approve", type="positive"
            ),
            on_reject=lambda command_id: ui.notify(
                f"Reject {command_id} via /api/commands/{{id}}/cancel", type="warning"
            ),
        )

    with ui.card().classes("w-full mt-6"):
        ui.label("Recent Commands").classes("text-lg font-semibold")
        ui.label("Executed, rejected, failed, and expired commands appear in the logs page.").classes(
            "text-sm opacity-70 mt-2"
        )


def _proposal_preview(
    group_id: str,
    greenhouse_id: str,
    zone_id: str,
    actuator: str,
    action: str,
    value: float | None,
    duration_seconds: float | int | None,
    reason: str,
) -> str:
    proposal = CommandPropose(
        group_id=UUID(group_id),
        greenhouse_id=UUID(greenhouse_id),
        zone_id=UUID(zone_id),
        actuator=actuator,
        action=action,
        value=value,
        duration_seconds=int(duration_seconds) if duration_seconds is not None else None,
        reason=reason,
        source="manual",
    )
    return f"Proposal ready: {proposal.actuator} {proposal.action} for {proposal.duration_seconds}s"


def command_to_action(command: Any) -> dict[str, Any]:
    return {
        "command_id": str(command.id),
        "group_id": str(command.group_id),
        "greenhouse_id": str(command.greenhouse_id),
        "zone_id": str(command.zone_id),
        "actuator": command.actuator_name,
        "action": command.action,
        "value": command.value,
        "duration_seconds": command.duration_seconds,
        "reason": command.reason,
        "status": command.status,
        "validation_errors": command.validation_errors,
    }


async def approve_command_for_ui(service: CommandService, command_id: UUID) -> dict[str, Any]:
    try:
        command = await service.approve(command_id, execute=True)
    except CommandError as exc:
        return {"status": "failed", "error": exc.message}
    return command_to_action(command)
