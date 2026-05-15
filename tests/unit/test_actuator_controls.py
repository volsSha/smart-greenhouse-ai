from __future__ import annotations

from app.ui.components.actuator_controls import (
    build_actuator_control_models,
    build_command_proposal_payload,
    clamp_duration,
    clamp_power,
)
from app.ui.components.control_panel_state import ScopeOption, ZoneContext

GROUP_ID = "00000000-0000-0000-0000-000000000001"
GREENHOUSE_ID = "00000000-0000-0000-0000-000000000002"
ZONE_ID = "00000000-0000-0000-0000-000000000003"


def _context() -> ZoneContext:
    return ZoneContext(
        group=ScopeOption(id=GROUP_ID, label="Main Group"),
        greenhouse=ScopeOption(id=GREENHOUSE_ID, label="North House"),
        zone=ScopeOption(id=ZONE_ID, label="Bed 1"),
    )


def test_build_actuator_control_models_reflect_safety_limits() -> None:
    models = {model.actuator: model for model in build_actuator_control_models()}

    assert models["pump"].supports_duration is True
    assert models["pump"].supports_power is False
    assert models["fan"].supports_power is True
    assert models["heater"].max_power == 80
    assert models["lamp"].max_duration_seconds == 3600


def test_clamp_duration_caps_at_actuator_limit() -> None:
    assert clamp_duration("pump", 120) == 60
    assert clamp_duration("pump", -1) == 0


def test_clamp_power_caps_at_actuator_limit() -> None:
    assert clamp_power("heater", 100) == 80
    assert clamp_power("heater", -10) == 0


def test_build_command_proposal_payload_uses_selected_scope() -> None:
    payload = build_command_proposal_payload(
        _context(),
        actuator="pump",
        action="on",
        duration_seconds=30,
        reason="Water bed 1",
    )

    assert payload["group_id"] == GROUP_ID
    assert payload["greenhouse_id"] == GREENHOUSE_ID
    assert payload["zone_id"] == ZONE_ID
    assert payload["actuator"] == "pump"
    assert payload["action"] == "on"
    assert payload["duration_seconds"] == 30
    assert payload["source"] == "manual"
    assert payload["mode"] == "mqtt"


def test_build_command_proposal_payload_includes_selected_mode() -> None:
    payload = build_command_proposal_payload(_context(), actuator="pump", action="on", mode="simulator")

    assert payload["mode"] == "simulator"


def test_build_command_proposal_payload_clamps_set_power() -> None:
    payload = build_command_proposal_payload(_context(), actuator="heater", action="set_power", value=95)

    assert payload["value"] == 80


def test_build_command_proposal_payload_omits_value_for_on_off() -> None:
    payload = build_command_proposal_payload(_context(), actuator="fan", action="on", value=50)

    assert payload["value"] is None
