"""Tests for AI agent response models."""

from __future__ import annotations

from app.services.ai_agent.models import AIResponse, AIResponseStatus


def test_ai_response_accepts_string_global_scope() -> None:
    response = AIResponse.model_validate(
        {
            "scope": "system_global",
            "status": "ok",
            "summary": "Hello!",
            "observations": [],
            "recommendations": [],
            "proposed_actions": [],
        }
    )

    assert response.scope.group_id is None
    assert response.scope.greenhouse_id is None
    assert response.scope.zone_id is None
    assert response.status == AIResponseStatus.OK
