"""Unit tests for AI response schemas."""

from __future__ import annotations

from pydantic import ValidationError

from app.services.ai_agent.models import AIResponse, AIResponseStatus, AIScope


def test_ai_response_accepts_minimal_structured_payload() -> None:
    """AIResponse validates the U10 structured output contract."""
    response = AIResponse(
        scope=AIScope(group_id="group-001"),
        status=AIResponseStatus.OK,
        summary="Greenhouse data is available.",
    )

    assert response.status == AIResponseStatus.OK
    assert response.scope.group_id == "group-001"
    assert response.observations == []
    assert response.recommendations == []
    assert response.proposed_actions == []


def test_proposed_actions_default_to_confirmation_required() -> None:
    """Physical action proposals are forced through approval flow."""
    response = AIResponse(
        scope=AIScope(
            group_id="group-001",
            greenhouse_id="gh-001",
            zone_id="zone-001",
        ),
        status="ok",
        summary="Soil moisture is below target.",
        proposed_actions=[
            {
                "group_id": "group-001",
                "greenhouse_id": "gh-001",
                "zone_id": "zone-001",
                "actuator": "pump",
                "action": "on",
                "duration_seconds": 30,
                "reason": "Soil moisture is below profile minimum.",
            }
        ],
    )

    assert response.proposed_actions[0]["requires_confirmation"] is True


def test_ai_response_rejects_unknown_top_level_fields() -> None:
    """Structured response should not silently accept out-of-contract fields."""
    try:
        AIResponse(
            scope=AIScope(),
            status="ok",
            summary="Valid summary",
            hidden_tool_data={"x": 1},
        )
    except ValidationError as exc:
        assert "hidden_tool_data" in str(exc)
    else:
        raise AssertionError("AIResponse accepted an unknown top-level field")
