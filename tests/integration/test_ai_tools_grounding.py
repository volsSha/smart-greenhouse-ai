"""Integration tests for AI tool grounding.

Tests that tools work end-to-end with mock ORM objects that behave like
real SQLAlchemy models (attribute access instead of mock magic).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.test import TestModel

from app.services.ai_agent.agent import GreenhouseAIAgent
from app.services.ai_agent.models import AIResponse, AIScope
from app.services.ai_agent.tools.deps import ToolDeps
from app.services.ai_agent.tools.group_tools import get_group_overview
from app.services.ai_agent.tools.greenhouse_tools import get_greenhouse_list, get_greenhouse_state
from app.services.ai_agent.tools.zone_tools import get_zone_state
from app.services.ai_agent.tools.alert_tools import get_active_alerts
from app.services.ai_agent.tools.command_tools import get_recent_commands
from app.services.ai_agent.tools.plant_tools import get_plant_batches, get_plant_profile
from app.services.ai_agent.tools.telemetry_tools import (
    get_today_group_summary,
    get_latest_readings,
)
from app.repositories.rag_repository import RAGRepository


# ---------------------------------------------------------------------------
# Helpers that create lightweight ORM-like objects (SimpleNamespace)
# ---------------------------------------------------------------------------

def _make_group_orm(**overrides) -> SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "name": "Integration Group",
        "location": "Test Farm",
        "description": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_greenhouse_orm(**overrides) -> SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "group_id": uuid.uuid4(),
        "name": "GH-Int",
        "location": "Field B",
        "description": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_zone_orm(**overrides) -> SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "greenhouse_id": uuid.uuid4(),
        "name": "Zone Int",
        "description": "Test zone",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_alert_orm(**overrides) -> SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "group_id": uuid.uuid4(),
        "greenhouse_id": uuid.uuid4(),
        "zone_id": uuid.uuid4(),
        "metric": "soil_moisture",
        "severity": "warning",
        "title": "Low soil moisture",
        "message": "Soil moisture dropped below threshold",
        "status": "active",
        "source": "threshold",
        "resolved_at": None,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_command_orm(**overrides) -> SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "group_id": uuid.uuid4(),
        "greenhouse_id": uuid.uuid4(),
        "zone_id": uuid.uuid4(),
        "actuator_id": None,
        "actuator_name": "pump",
        "action": "on",
        "value": None,
        "unit": None,
        "duration_seconds": 30,
        "source": "ai_agent",
        "reason": "Low soil moisture",
        "validation_errors": None,
        "status": "executed",
        "valid_until": None,
        "updated_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_batch_orm(**overrides) -> SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "zone_id": uuid.uuid4(),
        "name": "Tomatoes Int",
        "species": "Solanum lycopersicum",
        "cultivar": "Roma",
        "planted_at": datetime.now(timezone.utc).date(),
        "growth_stage": "flowering",
        "notes": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_profile_orm(**overrides) -> SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "crop_name": "Tomato",
        "growth_stage": "flowering",
        "temp_min": 18.0,
        "temp_opt": 24.0,
        "temp_max": 30.0,
        "humidity_min": 50.0,
        "humidity_opt": 65.0,
        "humidity_max": 80.0,
        "soil_moisture_min": 40.0,
        "soil_moisture_opt": 60.0,
        "soil_moisture_max": 80.0,
        "co2_min": 400.0,
        "co2_opt": 800.0,
        "co2_max": 1200.0,
        "light_min": 200.0,
        "light_opt": 500.0,
        "light_max": 800.0,
        "description": "Ideal for fruiting tomatoes",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_deps(**repo_overrides) -> ToolDeps:
    deps = ToolDeps(
        group_repo=AsyncMock(),
        greenhouse_repo=AsyncMock(),
        zone_repo=AsyncMock(),
        alert_repo=AsyncMock(),
        command_repo=AsyncMock(),
        plant_batch_repo=AsyncMock(),
        plant_profile_repo=AsyncMock(),
        telemetry_repo=MagicMock(),
        sensor_repo=AsyncMock(),
        actuator_repo=AsyncMock(),
        tool_logger=AsyncMock(),
    )
    for k, v in repo_overrides.items():
        setattr(deps, k, v)
    return deps


def _ctx(deps: ToolDeps) -> RunContext[ToolDeps]:
    ctx = MagicMock(spec=RunContext)
    ctx.deps = deps
    return ctx


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_group_overview_with_realistic_orm_objects() -> None:
    """get_group_overview works with SimpleNamespace ORM-like objects."""
    group = _make_group_orm()
    gh = _make_greenhouse_orm(group_id=group.id)
    zone = _make_zone_orm(greenhouse_id=gh.id)
    deps = _make_deps(
        group_repo=AsyncMock(list=AsyncMock(return_value=[group])),
        greenhouse_repo=AsyncMock(list=AsyncMock(return_value=[gh])),
        zone_repo=AsyncMock(list=AsyncMock(return_value=[zone])),
    )
    ctx = _ctx(deps)

    result = await get_group_overview(ctx)

    assert len(result) == 1
    assert result[0]["group_id"] == str(group.id)
    assert result[0]["name"] == "Integration Group"
    assert result[0]["greenhouse_count"] == 1
    assert result[0]["zone_count"] == 1


@pytest.mark.asyncio
async def test_greenhouse_list_walks_greenhouses() -> None:
    """get_greenhouse_list returns data from multiple greenhouses."""
    group_id = uuid.uuid4()
    gh1 = _make_greenhouse_orm(group_id=group_id, name="GH-1")
    gh2 = _make_greenhouse_orm(group_id=group_id, name="GH-2")
    deps = _make_deps(
        greenhouse_repo=AsyncMock(list=AsyncMock(return_value=[gh1, gh2])),
        zone_repo=AsyncMock(list=AsyncMock(return_value=[])),
    )
    ctx = _ctx(deps)

    result = await get_greenhouse_list(ctx, group_id=str(group_id))

    assert len(result) == 2
    names = {r["name"] for r in result}
    assert names == {"GH-1", "GH-2"}


@pytest.mark.asyncio
async def test_greenhouse_state_with_alerts_and_zones() -> None:
    """get_greenhouse_state correctly counts alerts per zone."""
    group_id = uuid.uuid4()
    gh = _make_greenhouse_orm(group_id=group_id)
    z1 = _make_zone_orm(greenhouse_id=gh.id, name="Zone-1")
    z2 = _make_zone_orm(greenhouse_id=gh.id, name="Zone-2")
    a1 = _make_alert_orm(group_id=group_id, greenhouse_id=gh.id, zone_id=z1.id)
    a2 = _make_alert_orm(group_id=group_id, greenhouse_id=gh.id, zone_id=z1.id)
    a3 = _make_alert_orm(group_id=group_id, greenhouse_id=gh.id, zone_id=z2.id)
    deps = _make_deps(
        greenhouse_repo=AsyncMock(get_by_id=AsyncMock(return_value=gh)),
        zone_repo=AsyncMock(list=AsyncMock(return_value=[z1, z2])),
        alert_repo=AsyncMock(list=AsyncMock(return_value=[a1, a2, a3])),
    )
    ctx = _ctx(deps)

    result = await get_greenhouse_state(ctx, str(group_id), str(gh.id))

    assert result["active_alert_count"] == 3
    assert len(result["zones"]) == 2


@pytest.mark.asyncio
async def test_zone_state_with_sensors_actuators_batches_alerts() -> None:
    """get_zone_state aggregates sensors, actuators, batches, and alerts."""
    group_id = uuid.uuid4()
    gh = _make_greenhouse_orm(group_id=group_id)
    zone = _make_zone_orm(greenhouse_id=gh.id)
    sensor = SimpleNamespace(id=uuid.uuid4(), zone_id=zone.id)
    actuator = SimpleNamespace(id=uuid.uuid4(), zone_id=zone.id)
    batch = _make_batch_orm(zone_id=zone.id)
    alert = _make_alert_orm(group_id=group_id, greenhouse_id=gh.id, zone_id=zone.id)
    deps = _make_deps(
        zone_repo=AsyncMock(get_by_id=AsyncMock(return_value=zone)),
        alert_repo=AsyncMock(list=AsyncMock(return_value=[alert])),
        sensor_repo=AsyncMock(list=AsyncMock(return_value=[sensor])),
        actuator_repo=AsyncMock(list=AsyncMock(return_value=[actuator])),
        plant_batch_repo=AsyncMock(list_by_zone=AsyncMock(return_value=[batch])),
    )
    ctx = _ctx(deps)

    result = await get_zone_state(ctx, str(group_id), str(gh.id), str(zone.id))

    assert result["sensor_count"] == 1
    assert result["actuator_count"] == 1
    assert len(result["plant_batches"]) == 1
    assert len(result["active_alerts"]) == 1
    assert result["active_alerts"][0]["severity"] == "warning"


@pytest.mark.asyncio
async def test_active_alerts_returns_serialized_dicts() -> None:
    """get_active_alerts serializes ORM objects to plain dicts."""
    group_id = uuid.uuid4()
    alert = _make_alert_orm(group_id=group_id)
    deps = _make_deps(
        alert_repo=AsyncMock(list=AsyncMock(return_value=[alert])),
    )
    ctx = _ctx(deps)

    result = await get_active_alerts(ctx, str(group_id))

    assert len(result) == 1
    entry = result[0]
    # Verify all string keys are present
    for key in ("alert_id", "severity", "title", "message", "source", "created_at"):
        assert key in entry, f"Missing key: {key}"
    # Verify UUID fields are serialized to strings
    assert isinstance(entry["alert_id"], str)
    assert isinstance(entry["group_id"], str)


@pytest.mark.asyncio
async def test_recent_commands_returns_serialized_dicts() -> None:
    """get_recent_commands serializes CommandLog ORM objects to plain dicts."""
    group_id = uuid.uuid4()
    cmd = _make_command_orm(group_id=group_id)
    deps = _make_deps(
        command_repo=AsyncMock(get_recent=AsyncMock(return_value=[cmd])),
    )
    ctx = _ctx(deps)

    result = await get_recent_commands(ctx, str(group_id))

    assert len(result) == 1
    entry = result[0]
    for key in ("command_id", "actuator", "action", "status", "source", "created_at"):
        assert key in entry, f"Missing key: {key}"
    assert entry["actuator"] == "pump"
    assert entry["action"] == "on"


@pytest.mark.asyncio
async def test_plant_batches_across_greenhouses_and_zones() -> None:
    """get_plant_batches collects batches from all zones in all greenhouses."""
    group_id = uuid.uuid4()
    gh1 = _make_greenhouse_orm(group_id=group_id, name="GH-A")
    gh2 = _make_greenhouse_orm(group_id=group_id, name="GH-B")
    z1 = _make_zone_orm(greenhouse_id=gh1.id, name="Z1")
    z2 = _make_zone_orm(greenhouse_id=gh2.id, name="Z2")
    b1 = _make_batch_orm(zone_id=z1.id, name="Tomatoes")
    b2 = _make_batch_orm(zone_id=z2.id, name="Lettuce")
    deps = _make_deps(
        greenhouse_repo=AsyncMock(list=AsyncMock(return_value=[gh1, gh2])),
        zone_repo=AsyncMock(
            list=AsyncMock(
                side_effect=lambda **kw: [z1] if kw.get("greenhouse_id") == gh1.id else [z2]
            )
        ),
        plant_batch_repo=AsyncMock(
            list_by_zone=AsyncMock(
                side_effect=lambda zid: [b1] if zid == z1.id else [b2]
            )
        ),
    )
    ctx = _ctx(deps)

    result = await get_plant_batches(ctx, str(group_id))

    assert len(result) == 2
    names = {r["name"] for r in result}
    assert names == {"Tomatoes", "Lettuce"}


@pytest.mark.asyncio
async def test_plant_profile_returns_threshold_ranges() -> None:
    """get_plant_profile returns a complete profile with all threshold ranges."""
    profile = _make_profile_orm()
    deps = _make_deps(
        plant_profile_repo=AsyncMock(get_by_id=AsyncMock(return_value=profile)),
    )
    ctx = _ctx(deps)

    result = await get_plant_profile(ctx, str(profile.id))

    assert result["crop_name"] == "Tomato"
    for category in ("temperature", "humidity", "soil_moisture", "co2", "light"):
        assert category in result, f"Missing category: {category}"
        assert "min" in result[category]
        assert "optimal" in result[category]
        assert "max" in result[category]


@pytest.mark.asyncio
async def test_telemetry_summary_delegates_to_influx() -> None:
    """Telemetry tools pass through to the InfluxDB-backed repository."""
    fake_summary = [
        {"metric": "temperature", "min": 18.0, "max": 30.0, "latest": 24.5},
        {"metric": "humidity", "min": 50.0, "max": 80.0, "latest": 65.0},
    ]
    telemetry_repo = MagicMock()
    telemetry_repo.get_group_summary.return_value = fake_summary
    deps = _make_deps(telemetry_repo=telemetry_repo)
    ctx = _ctx(deps)

    result = await get_today_group_summary(ctx, "grp-001")

    assert len(result) == 2
    assert result[0]["metric"] == "temperature"
    telemetry_repo.get_group_summary.assert_called_once_with("grp-001")


@pytest.mark.asyncio
async def test_latest_readings_with_scoped_filters() -> None:
    """get_latest_readings passes through all filter params."""
    fake_readings = [{"metric": "co2", "_value": 600.0, "zone_id": "z1"}]
    telemetry_repo = MagicMock()
    telemetry_repo.get_latest.return_value = fake_readings
    deps = _make_deps(telemetry_repo=telemetry_repo)
    ctx = _ctx(deps)

    result = await get_latest_readings(
        ctx, "grp-001",
        greenhouse_id="gh-001",
        zone_id="z1",
    )

    assert result == fake_readings
    telemetry_repo.get_latest.assert_called_once_with(
        "grp-001", greenhouse_id="gh-001", zone_id="z1",
    )


@pytest.mark.asyncio
async def test_tools_registered_on_agent() -> None:
    """GreenhouseAIAgent registers all read-only tools at construction."""
    session = MagicMock()
    output = AIResponse(
        scope=AIScope(group_id="grp-001"),
        status="ok",
        summary="Tools are available.",
    )
    test_agent = Agent(TestModel(custom_output_args=output), output_type=AIResponse, deps_type=ToolDeps)
    from unittest.mock import patch
    with patch.object(GreenhouseAIAgent, '_build_agent', return_value=test_agent):
        service = GreenhouseAIAgent.__new__(GreenhouseAIAgent)
        service.session = session
        service.settings = MagicMock()
        service.conversation_repository = MagicMock()
        service.tool_log_repository = MagicMock()
        service.tool_logger = MagicMock()
        service.agent = test_agent
        service.register_tools()

    # Verify tools were registered by checking the agent's function toolset
    tool_names = [t.name for t in test_agent._function_toolset.tools.values()]
    assert "get_group_overview" in tool_names
    assert "get_greenhouse_list" in tool_names
    assert "get_greenhouse_state" in tool_names
    assert "compare_greenhouses" in tool_names
    assert "get_zone_state" in tool_names
    assert "get_zone_plant_info" in tool_names
    assert "get_plant_batches" in tool_names
    assert "get_plant_profile" in tool_names
    assert "get_today_group_summary" in tool_names
    assert "get_today_greenhouse_summary" in tool_names
    assert "get_today_zone_summary" in tool_names
    assert "get_latest_readings" in tool_names
    assert "get_active_alerts" in tool_names
    assert "get_recent_commands" in tool_names


def test_agent_deps_include_rag_repo_and_settings() -> None:
    session = MagicMock()
    settings = MagicMock()
    test_agent = MagicMock()
    service = GreenhouseAIAgent(session, settings=settings, agent=test_agent)

    deps = service._build_deps()

    assert isinstance(deps.rag_repo, RAGRepository)
    assert deps.settings is settings
