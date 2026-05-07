"""System-level AI grounding invariants."""

from __future__ import annotations

from app.services.ai_agent.models import AIResponse, AIResponseStatus, AIScope
from app.services.ai_agent.tools import ALL_TOOLS


def test_ai_grounding_tools_cover_operational_state_and_rag() -> None:
    names = {tool.__name__ for tool in ALL_TOOLS}

    assert "get_group_overview" in names
    assert "compare_greenhouses" in names
    assert "get_zone_state" in names
    assert "get_active_alerts" in names
    assert "get_recent_commands" in names
    assert "search_plant_knowledge" in names


def test_ai_response_can_represent_scoped_grounded_answer() -> None:
    response = AIResponse(
        scope=AIScope(group_id="group-001", greenhouse_id="gh-001", zone_id="zone-01"),
        status=AIResponseStatus.OK,
        summary="Greenhouse gh-001 is stable with one watering recommendation.",
        observations=["Zone zone-01 soil moisture is below target."],
        recommendations=["Review the proposed watering action before approval."],
    )

    assert response.scope.group_id == "group-001"
    assert response.status == "ok"
    assert response.observations
