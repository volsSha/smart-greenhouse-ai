"""Tests for AI proposed action safety boundaries."""

from __future__ import annotations

from app.services.ai_agent.models import AIResponse, AIResponseStatus, AIScope
from app.services.ai_agent.tools import ALL_TOOLS


def test_ai_response_marks_proposed_actions_for_confirmation() -> None:
    response = AIResponse(
        scope=AIScope(group_id="group-001", greenhouse_id="gh-001", zone_id="zone-01"),
        status=AIResponseStatus.OK,
        summary="Soil is dry.",
        proposed_actions=[{"actuator": "pump", "action": "on", "duration_seconds": 30}],
    )

    assert response.proposed_actions[0]["requires_confirmation"] is True


def test_ai_tools_can_propose_but_not_execute_mqtt_commands() -> None:
    tool_names = {tool.__name__ for tool in ALL_TOOLS}

    assert "propose_watering_action" in tool_names
    assert "propose_ventilation_action" in tool_names
    assert "propose_lighting_action" in tool_names
    assert "propose_heater_setpoint_action" in tool_names
    assert "execute_command" not in tool_names
    assert "publish_command" not in tool_names
