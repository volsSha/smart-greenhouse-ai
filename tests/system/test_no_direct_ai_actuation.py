"""System-level safety invariant: no direct AI or control actuation."""

from __future__ import annotations

from app.services.ai_agent.tools import ALL_TOOLS
from services.control_engine.rules import evaluate_zone_rules


def test_ai_tool_registry_exposes_no_direct_mqtt_execution_tool() -> None:
    names = {tool.__name__ for tool in ALL_TOOLS}

    forbidden = {"execute_command", "publish_command", "send_mqtt_command"}
    assert names.isdisjoint(forbidden)
    assert any(name.startswith("propose_") for name in names)


def test_control_engine_rules_only_return_proposals() -> None:
    proposals = evaluate_zone_rules

    assert callable(proposals)
    assert not hasattr(proposals, "publish")
