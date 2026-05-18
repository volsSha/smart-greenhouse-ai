"""Actuator control models and rendering for proposal-only commands."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from nicegui import ui

from app.core.safety_limits import SAFETY_LIMITS, VALID_ACTIONS_PER_ACTUATOR
from app.i18n.core import _
from app.schemas.commands import CommandPropose
from app.ui.components.control_panel_state import ZoneContext

ACTUATOR_LABELS = {
    "pump": "Pump",
    "fan": "Fan",
    "heater": "Heater",
    "lamp": "Lamp",
}


@dataclass(frozen=True)
class ActuatorControlModel:
    actuator: str
    label: str
    actions: list[str]
    max_duration_seconds: int | None = None
    max_power: int | None = None
    supports_duration: bool = False
    supports_power: bool = False


def build_actuator_control_models() -> list[ActuatorControlModel]:
    models: list[ActuatorControlModel] = []
    for actuator, limits in SAFETY_LIMITS.items():
        max_power = limits.get("max_power")
        max_duration = limits.get("max_duration_seconds")
        models.append(
            ActuatorControlModel(
                actuator=actuator,
                label=ACTUATOR_LABELS.get(actuator, actuator.title()),
                actions=sorted(VALID_ACTIONS_PER_ACTUATOR.get(actuator, set())),
                max_duration_seconds=max_duration,
                max_power=max_power,
                supports_duration=max_duration is not None,
                supports_power=max_power is not None,
            )
        )
    return models


def clamp_duration(actuator: str, duration_seconds: int | None) -> int | None:
    if duration_seconds is None:
        return None
    max_duration = SAFETY_LIMITS.get(actuator, {}).get("max_duration_seconds")
    if max_duration is None:
        return duration_seconds
    return max(0, min(int(duration_seconds), int(max_duration)))


def clamp_power(actuator: str, value: float | None) -> float | None:
    if value is None:
        return None
    max_power = SAFETY_LIMITS.get(actuator, {}).get("max_power")
    if max_power is None:
        return value
    return max(0.0, min(float(value), float(max_power)))


def build_command_proposal_payload(
    zone_context: ZoneContext,
    *,
    actuator: str,
    action: str,
    value: float | None = None,
    duration_seconds: int | None = None,
    reason: str | None = None,
    mode: str = "mqtt",
) -> dict[str, object]:
    if action == "set_power":
        value = clamp_power(actuator, value)
    else:
        value = None

    proposal = CommandPropose(
        group_id=UUID(zone_context.group.id),
        greenhouse_id=UUID(zone_context.greenhouse.id),
        zone_id=UUID(zone_context.zone.id),
        actuator=actuator,
        action=action,
        value=value,
        duration_seconds=clamp_duration(actuator, duration_seconds),
        reason=reason or _("Operator requested {actuator} {action}", actuator=actuator, action=action),
        source="manual",
        mode=mode,
    )
    return proposal.model_dump(mode="json")


def render_actuator_controls(zone_context: ZoneContext, on_propose, *, mode: str = "mqtt", disabled: bool = False) -> None:
    with ui.column().classes("w-full gap-3"):
        for model in build_actuator_control_models():
            with ui.card().classes("control-actuator-card w-full p-3"):
                with ui.row().classes("w-full items-center justify-between gap-2"):
                    ui.label(_(model.label)).classes("font-semibold")
                    ui.badge(_("Proposal only"), color="blue").props("outline")

                duration = None
                power = None
                if model.supports_duration:
                    duration = ui.number(
                        label=_("Duration (s)"),
                        value=min(30, model.max_duration_seconds or 30),
                        min=0,
                        max=model.max_duration_seconds,
                    ).classes("w-36")
                if model.supports_power:
                    power = ui.slider(min=0, max=model.max_power or 100, value=min(50, model.max_power or 50)).props("label-always")

                with ui.row().classes("gap-2 flex-wrap mt-2"):
                    for action in model.actions:
                        def propose(
                            action_name: str = action,
                            control_model: ActuatorControlModel = model,
                            power_control=power,
                            duration_control=duration,
                        ) -> None:
                            payload = build_command_proposal_payload(
                                zone_context,
                                actuator=control_model.actuator,
                                action=action_name,
                                value=power_control.value if power_control is not None and action_name == "set_power" else None,
                                duration_seconds=int(duration_control.value) if duration_control is not None and duration_control.value is not None else None,
                                mode=mode,
                            )
                            on_propose(payload)

                        button = ui.button(_(action.replace("_", " ").title()), on_click=propose).props("outline")
                        if disabled:
                            button.disable()
