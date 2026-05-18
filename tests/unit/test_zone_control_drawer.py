from __future__ import annotations

from app.ui.components.control_panel_state import ScopeOption, ZoneContext
from app.ui.components.zone_control_drawer import command_to_action


def test_command_to_action_adds_scope_label() -> None:
    context = ZoneContext(
        group=ScopeOption(id="group-id", label="Main Group"),
        greenhouse=ScopeOption(id="gh-id", label="North House"),
        zone=ScopeOption(id="zone-id", label="Bed 1"),
    )

    action = command_to_action(
        {
            "id": "command-id",
            "group_id": "group-id",
            "greenhouse_id": "gh-id",
            "zone_id": "zone-id",
            "actuator_name": "pump",
            "action": "on",
            "status": "proposed",
        },
        context,
    )

    assert action["command_id"] == "command-id"
    assert action["scope_label"] == "Main Group / North House / Bed 1"
    assert action["actuator"] == "pump"
