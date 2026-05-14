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
from app.ui.components.design import empty_state, page_container, page_hero, section_card
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

    with page_container():
        page_hero(
            _("Actuator Control"),
            _("Propose, validate, approve, and execute physical actuator commands with safety gates."),
            icon="tune",
            meta=_("Command center"),
        )

        notification = ui.notification(position="top", timeout=5)

        with section_card(_("Propose Command"), _("Target a zone, choose an actuator action, and explain the operational reason."), icon="add_task"):
            with ui.row().classes("w-full gap-4 mt-4 flex-wrap"):
                group_id = ui.input(_("Group ID"), value=_SAMPLE_GROUP_ID).classes("w-80")
                greenhouse_id = ui.input(_("Greenhouse ID"), value=_SAMPLE_GREENHOUSE_ID).classes("w-80")
                zone_id = ui.input(_("Zone ID"), value=_SAMPLE_ZONE_ID).classes("w-80")
            with ui.row().classes("w-full gap-4 mt-4 flex-wrap"):
                actuator = ui.select(label=_("Actuator"), options=["pump", "fan", "heater", "lamp"], value="pump").classes("w-48")
                action = ui.select(label=_("Action"), options=["on", "off", "set_power"], value="on").classes("w-48")
                value = ui.number(label=_("Value"), value=None).classes("w-32")
                duration = ui.number(label=_("Duration (s)"), value=30).classes("w-32")
            reason = ui.textarea(label=_("Reason"), value=_("Manual greenhouse adjustment")).classes("w-full mt-4")
            ui.button(_("Propose"), color="primary", on_click=lambda: propose_command()).classes("mt-3")

        with section_card(_("Pending Commands"), _("Validated and AI-generated proposals require approval before MQTT execution."), icon="pending_actions"):
            pending_commands = ui.column().classes("w-full gap-3 mt-4")

        with section_card(_("Recent Commands"), _("Executed, rejected, failed, and expired commands appear here."), icon="history"):
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
                empty_state(_("Enter a valid Group ID"), _("Commands are loaded by group scope."), icon="badge")
            return

        try:
            async with api_client(timeout=10.0) as client:
                response = await client.get(f"/api/commands/groups/{group_id.value}/recent")
                if response.status_code != 200:
                    with pending_commands:
                        empty_state(_("Failed to load commands"), response_error(response), icon="sync_problem")
                    return
                commands = response.json()
        except httpx.HTTPError as exc:
            with pending_commands:
                empty_state(_("Failed to load commands"), str(exc), icon="sync_problem")
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
                empty_state(_("No pending commands"), _("Validated proposals will appear here before approval."), icon="task_alt")
            for command in pending:
                proposed_action_card(
                    command_to_action(command),
                    on_approve=lambda command_id: approve_command(command_id),
                    on_reject=lambda command_id: reject_command(command_id),
                )

        with recent_commands:
            if not completed:
                empty_state(_("No recent completed commands"), _("Executed, rejected, failed, and expired commands will be listed here."), icon="history")
            for command in completed[:10]:
                with ui.row().classes("greenhouse-card w-full items-center justify-between p-3 rounded"):
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
