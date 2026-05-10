"""Control page -- actuator command proposal and approval interface."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
from nicegui import ui

from app.i18n.core import _
from app.schemas.commands import CommandPropose
from app.services.command_service import CommandStatus
from app.ui.api_client import api_client, response_error
from app.ui.components.proposed_action_card import proposed_action_card
from app.ui.layouts.main_layout import main_layout

_SAMPLE_GROUP_ID = "00000000-0000-0000-0000-000000000001"
_SAMPLE_GREENHOUSE_ID = "00000000-0000-0000-0000-000000000002"
_SAMPLE_ZONE_ID = "00000000-0000-0000-0000-000000000003"
_PENDING_STATUSES = {
    CommandStatus.PROPOSED,
    CommandStatus.VALIDATED,
    CommandStatus.APPROVED,
}


@ui.page("/control")
async def control() -> None:
    """Render the actuator control page."""
    main_layout()

    ui.label(_("Actuator Control")).classes("text-2xl font-bold mt-6")
    ui.label(_("Propose, validate, approve, and execute actuator commands.")).classes(
        "text-sm opacity-70 mt-2"
    )

    notification = ui.notification(position="top", timeout=5)

    with ui.card().classes("w-full mt-6"):
        ui.label(_("Propose Command")).classes("text-lg font-semibold")
        with ui.row().classes("w-full gap-4 mt-4"):
            group_id = ui.input(_("Group ID"), value=_SAMPLE_GROUP_ID).classes("w-80")
            greenhouse_id = ui.input(_("Greenhouse ID"), value=_SAMPLE_GREENHOUSE_ID).classes("w-80")
            zone_id = ui.input(_("Zone ID"), value=_SAMPLE_ZONE_ID).classes("w-80")
        with ui.row().classes("w-full gap-4 mt-4"):
            actuator = ui.select(
                label=_("Actuator"),
                options=["pump", "fan", "heater", "lamp"],
                value="pump",
            ).classes("w-48")
            action = ui.select(
                label=_("Action"),
                options=["on", "off", "set_power"],
                value="on",
            ).classes("w-48")
            value = ui.number(label=_("Value"), value=None).classes("w-32")
            duration = ui.number(label=_("Duration (s)"), value=30).classes("w-32")
        reason = ui.textarea(label=_("Reason"), value=_("Manual greenhouse adjustment")).classes("w-full mt-4")
        ui.button(
            _("Propose"),
            color="primary",
            on_click=lambda: propose_command(),
        )

    with ui.card().classes("w-full mt-6"):
        ui.label(_("Pending Commands")).classes("text-lg font-semibold")
        ui.label(
            _("Validated and AI-generated proposals require approval before MQTT execution.")
        ).classes("text-sm opacity-70 mt-2")
        pending_commands = ui.column().classes("w-full gap-2 mt-4")

    with ui.card().classes("w-full mt-6"):
        ui.label(_("Recent Commands")).classes("text-lg font-semibold")
        ui.label(_("Executed, rejected, failed, and expired commands appear here.")).classes(
            "text-sm opacity-70 mt-2"
        )
        recent_commands = ui.column().classes("w-full gap-2 mt-4")

    def notify(message: str, kind: str = "info") -> None:
        notification.set_message(message)
        notification.set_type(kind)
        notification.open()

    def build_proposal() -> dict[str, Any] | None:
        try:
            proposal = CommandPropose(
                group_id=UUID(group_id.value or ""),
                greenhouse_id=UUID(greenhouse_id.value or ""),
                zone_id=UUID(zone_id.value or ""),
                actuator=str(actuator.value),
                action=str(action.value),
                value=value.value,
                duration_seconds=int(duration.value) if duration.value is not None else None,
                reason=reason.value,
                source="manual",
            )
        except (TypeError, ValueError) as exc:
            notify(_("Invalid command form: {error}", error=exc), "warning")
            return None
        return proposal.model_dump(mode="json")

    async def post_command_action(
        endpoint: str,
        *,
        expected_status: int,
        success_message: str,
        failure_prefix: str,
        payload: dict[str, Any] | None = None,
        timeout: float = 10.0,
        success_type: str = "positive",
    ) -> bool:
        try:
            async with api_client(timeout=timeout) as client:
                response = await client.post(endpoint, json=payload)
                if response.status_code != expected_status:
                    notify(_("{prefix}: {error}", prefix=failure_prefix, error=response_error(response)), "negative")
                    return False
        except httpx.HTTPError as exc:
            notify(_("{prefix}: {error}", prefix=failure_prefix, error=exc), "negative")
            return False
        notify(success_message, success_type)
        await refresh_commands()
        return True

    async def propose_command() -> None:
        payload = build_proposal()
        if payload is None:
            return
        await post_command_action(
            "/api/commands/propose",
            expected_status=201,
            success_message=_("Command proposed"),
            failure_prefix=_("Propose failed"),
            payload=payload,
        )

    async def approve_command(command_id: str) -> None:
        await post_command_action(
            f"/api/commands/{command_id}/approve",
            expected_status=200,
            success_message=_("Command approved"),
            failure_prefix=_("Approve failed"),
            timeout=15.0,
        )

    async def reject_command(command_id: str) -> None:
        await post_command_action(
            f"/api/commands/{command_id}/cancel",
            expected_status=200,
            success_message=_("Command rejected"),
            failure_prefix=_("Reject failed"),
            success_type="warning",
        )

    async def refresh_commands() -> None:
        pending_commands.clear()
        recent_commands.clear()
        try:
            UUID(group_id.value or "")
        except ValueError:
            with pending_commands:
                ui.label(_("Enter a valid Group ID to load commands.")).classes("text-sm opacity-60")
            return

        try:
            async with api_client(timeout=10.0) as client:
                response = await client.get(f"/api/commands/groups/{group_id.value}/recent")
                if response.status_code != 200:
                    with pending_commands:
                        ui.label(_("Failed to load commands: {error}", error=response_error(response))).classes("text-sm text-red-500")
                    return
                commands = response.json()
        except httpx.HTTPError as exc:
            with pending_commands:
                ui.label(_("Failed to load commands: {error}", error=exc)).classes("text-sm text-red-500")
            return

        pending: list[dict[str, Any]] = []
        completed: list[dict[str, Any]] = []
        for command in commands:
            if command.get("status") in _PENDING_STATUSES:
                pending.append(command)
                continue
            completed.append(command)

        with pending_commands:
            if not pending:
                ui.label(_("No pending commands.")).classes("text-sm opacity-60")
            for command in pending:
                proposed_action_card(
                    command_to_action(command),
                    on_approve=lambda command_id: approve_command(command_id),
                    on_reject=lambda command_id: reject_command(command_id),
                )

        with recent_commands:
            if not completed:
                ui.label(_("No recent completed commands.")).classes("text-sm opacity-60")
            for command in completed[:10]:
                with ui.row().classes("w-full items-center justify-between p-2 border border-gray-200 rounded"):
                    ui.label(f"{command['actuator_name']} -> {command['action']}").classes("font-medium")
                    ui.badge(command["status"], color="blue")

    await refresh_commands()


def command_to_action(command: dict[str, Any]) -> dict[str, Any]:
    return {
        "command_id": str(command["id"]),
        "group_id": str(command["group_id"]),
        "greenhouse_id": str(command["greenhouse_id"]),
        "zone_id": str(command["zone_id"]),
        "actuator": command["actuator_name"],
        "action": command["action"],
        "value": command.get("value"),
        "duration_seconds": command.get("duration_seconds"),
        "reason": command.get("reason"),
        "status": command.get("status"),
        "validation_errors": command.get("validation_errors"),
    }
