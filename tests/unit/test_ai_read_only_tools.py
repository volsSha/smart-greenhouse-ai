"""Unit tests for read-only AI tools.

Each tool is tested with mocked repositories to verify it returns the
expected data shape and delegates to the correct repository methods.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai import RunContext

from app.services.ai_agent.tools.alert_tools import get_active_alerts
from app.services.ai_agent.tools.command_tools import get_recent_commands
from app.services.ai_agent.tools.deps import ToolDeps
from app.services.ai_agent.tools.greenhouse_tools import (
    compare_greenhouses,
    get_greenhouse_list,
    get_greenhouse_state,
)
from app.services.ai_agent.tools.group_tools import get_group_overview
from app.services.ai_agent.tools.plant_tools import get_plant_batches, get_plant_profile
from app.services.ai_agent.tools.telemetry_tools import (
    get_latest_readings,
    get_today_greenhouse_summary,
    get_today_group_summary,
    get_today_zone_summary,
)
from app.services.ai_agent.tools.zone_tools import get_zone_plant_info, get_zone_state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GROUP_ID = uuid.uuid4()
GREENHOUSE_ID = uuid.uuid4()
ZONE_ID = uuid.uuid4()


def _make_group(**overrides):
    g = MagicMock()
    g.id = GROUP_ID
    g.name = "Test Group"
    g.location = "Test Farm"
    for k, v in overrides.items():
        setattr(g, k, v)
    return g


def _make_greenhouse(**overrides):
    gh = MagicMock()
    gh.id = GREENHOUSE_ID
    gh.name = "GH-1"
    gh.location = "Field A"
    gh.group_id = GROUP_ID
    for k, v in overrides.items():
        setattr(gh, k, v)
    return gh


def _make_zone(**overrides):
    z = MagicMock()
    z.id = ZONE_ID
    z.name = "Zone A"
    z.description = "Growing area"
    z.greenhouse_id = GREENHOUSE_ID
    for k, v in overrides.items():
        setattr(z, k, v)
    return z


def _make_alert(**overrides):
    a = MagicMock()
    a.id = uuid.uuid4()
    a.group_id = GROUP_ID
    a.greenhouse_id = GREENHOUSE_ID
    a.zone_id = ZONE_ID
    a.severity = "warning"
    a.title = "Low moisture"
    a.message = "Soil moisture below threshold"
    a.metric = "soil_moisture"
    a.status = "active"
    a.source = "threshold"
    a.created_at = datetime.now(timezone.utc)
    for k, v in overrides.items():
        setattr(a, k, v)
    return a


def _make_batch(**overrides):
    b = MagicMock()
    b.id = uuid.uuid4()
    b.zone_id = ZONE_ID
    b.name = "Tomatoes"
    b.species = "Solanum lycopersicum"
    b.cultivar = "Roma"
    b.planted_at = datetime.now(timezone.utc).date()
    b.growth_stage = "flowering"
    b.profile_id = None
    b.notes = None
    for k, v in overrides.items():
        setattr(b, k, v)
    return b


def _make_command(**overrides):
    c = MagicMock()
    c.id = uuid.uuid4()
    c.group_id = GROUP_ID
    c.greenhouse_id = GREENHOUSE_ID
    c.zone_id = ZONE_ID
    c.actuator_name = "pump"
    c.action = "on"
    c.value = None
    c.unit = None
    c.duration_seconds = 30
    c.status = "executed"
    c.source = "ai_agent"
    c.reason = "Low soil moisture"
    c.created_at = datetime.now(timezone.utc)
    for k, v in overrides.items():
        setattr(c, k, v)
    return c


def _make_deps(**repo_overrides) -> ToolDeps:
    """Build a ToolDeps with mocked repos."""
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
    """Create a mock RunContext carrying the given deps."""
    ctx = MagicMock(spec=RunContext)
    ctx.deps = deps
    return ctx


# ---------------------------------------------------------------------------
# Group tools
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_group_overview_returns_shape() -> None:
    """get_group_overview returns list of dicts with expected keys."""
    group = _make_group()
    gh = _make_greenhouse()
    zone = _make_zone()
    deps = _make_deps(
        group_repo=AsyncMock(list=AsyncMock(return_value=[group])),
        greenhouse_repo=AsyncMock(list=AsyncMock(return_value=[gh])),
        zone_repo=AsyncMock(list=AsyncMock(return_value=[zone])),
    )
    ctx = _ctx(deps)

    result = await get_group_overview(ctx)

    assert isinstance(result, list)
    assert len(result) == 1
    entry = result[0]
    assert "group_id" in entry
    assert "name" in entry
    assert "location" in entry
    assert "greenhouse_count" in entry
    assert "zone_count" in entry
    assert entry["greenhouse_count"] == 1
    assert entry["zone_count"] == 1


@pytest.mark.asyncio
async def test_get_group_overview_empty() -> None:
    """get_group_overview returns empty list when no groups."""
    deps = _make_deps(group_repo=AsyncMock(list=AsyncMock(return_value=[])))
    deps.telemetry_repo.get_latest.return_value = []
    ctx = _ctx(deps)

    result = await get_group_overview(ctx)

    assert result == []


@pytest.mark.asyncio
async def test_get_group_overview_uses_telemetry_when_registry_empty() -> None:
    """get_group_overview derives group data from telemetry when registry is empty."""
    deps = _make_deps(group_repo=AsyncMock(list=AsyncMock(return_value=[])))
    deps.telemetry_repo.get_latest.return_value = [
        {"group_id": "group-001", "greenhouse_id": "gh-001", "zone_id": "zone-01"},
        {"group_id": "group-001", "greenhouse_id": "gh-002", "zone_id": "zone-02"},
    ]
    ctx = _ctx(deps)

    result = await get_group_overview(ctx)

    assert result == [
        {
            "group_id": "group-001",
            "name": "group-001",
            "location": None,
            "greenhouse_count": 2,
            "zone_count": 2,
            "source": "telemetry",
        }
    ]


# ---------------------------------------------------------------------------
# Greenhouse tools
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_greenhouse_list_returns_shape() -> None:
    """get_greenhouse_list returns list with greenhouse_id, name, location, zone_count."""
    gh = _make_greenhouse()
    zone = _make_zone()
    deps = _make_deps(
        greenhouse_repo=AsyncMock(list=AsyncMock(return_value=[gh])),
        zone_repo=AsyncMock(list=AsyncMock(return_value=[zone])),
    )
    ctx = _ctx(deps)

    result = await get_greenhouse_list(ctx, group_id=str(GROUP_ID))

    assert isinstance(result, list)
    assert len(result) == 1
    entry = result[0]
    assert entry["greenhouse_id"] == str(GREENHOUSE_ID)
    assert entry["name"] == "GH-1"
    assert "location" in entry
    assert entry["zone_count"] == 1


@pytest.mark.asyncio
async def test_get_greenhouse_list_uses_telemetry_ids() -> None:
    """get_greenhouse_list supports simulator IDs from telemetry."""
    deps = _make_deps()
    deps.telemetry_repo.get_latest.return_value = [
        {"greenhouse_id": "gh-001", "zone_id": "zone-01"},
        {"greenhouse_id": "gh-001", "zone_id": "zone-02"},
        {"greenhouse_id": "gh-002", "zone_id": "zone-01"},
    ]
    ctx = _ctx(deps)

    result = await get_greenhouse_list(ctx, group_id="group-001")

    assert [item["greenhouse_id"] for item in result] == ["gh-001", "gh-002"]
    assert result[0]["zone_count"] == 2
    assert result[0]["source"] == "telemetry"


@pytest.mark.asyncio
async def test_get_greenhouse_state_uses_telemetry_ids() -> None:
    """get_greenhouse_state supports simulator IDs from telemetry."""
    deps = _make_deps()
    deps.telemetry_repo.get_latest.return_value = [
        {"zone_id": "zone-01", "metric": "temperature", "_value": 24.0},
        {"zone_id": "zone-01", "metric": "soil_moisture", "_value": 58.0},
    ]
    ctx = _ctx(deps)

    result = await get_greenhouse_state(ctx, "group-001", "gh-001")

    assert result["greenhouse_id"] == "gh-001"
    assert result["source"] == "telemetry"
    assert result["zones"][0]["latest_metrics"]["temperature"] == 24.0


@pytest.mark.asyncio
async def test_get_greenhouse_state_returns_shape() -> None:
    """get_greenhouse_state returns dict with zones and active alerts."""
    gh = _make_greenhouse()
    zone = _make_zone()
    alert = _make_alert()
    deps = _make_deps(
        greenhouse_repo=AsyncMock(get_by_id=AsyncMock(return_value=gh)),
        zone_repo=AsyncMock(list=AsyncMock(return_value=[zone])),
        alert_repo=AsyncMock(list=AsyncMock(return_value=[alert])),
    )
    ctx = _ctx(deps)

    result = await get_greenhouse_state(ctx, str(GROUP_ID), str(GREENHOUSE_ID))

    assert result["greenhouse_id"] == str(GREENHOUSE_ID)
    assert result["name"] == "GH-1"
    assert "zones" in result
    assert len(result["zones"]) == 1
    assert result["active_alert_count"] == 1


@pytest.mark.asyncio
async def test_get_greenhouse_state_not_found() -> None:
    """get_greenhouse_state returns error dict when greenhouse missing."""
    deps = _make_deps(
        greenhouse_repo=AsyncMock(get_by_id=AsyncMock(return_value=None)),
    )
    ctx = _ctx(deps)

    result = await get_greenhouse_state(ctx, str(GROUP_ID), str(GREENHOUSE_ID))

    assert "error" in result
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_compare_greenhouses_returns_shape() -> None:
    """compare_greenhouses returns list of greenhouse summaries."""
    gh = _make_greenhouse()
    zone = _make_zone()
    deps = _make_deps(
        greenhouse_repo=AsyncMock(list=AsyncMock(return_value=[gh])),
        zone_repo=AsyncMock(list=AsyncMock(return_value=[zone])),
        alert_repo=AsyncMock(list=AsyncMock(return_value=[])),
    )
    ctx = _ctx(deps)

    result = await compare_greenhouses(ctx, str(GROUP_ID))

    assert isinstance(result, list)
    assert len(result) == 1
    entry = result[0]
    assert "greenhouse_id" in entry
    assert "name" in entry
    assert "zone_count" in entry
    assert "active_alert_count" in entry


# ---------------------------------------------------------------------------
# Zone tools
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_zone_state_returns_shape() -> None:
    """get_zone_state returns dict with sensors, actuators, plants, alerts."""
    zone = _make_zone()
    alert = _make_alert()
    batch = _make_batch()
    deps = _make_deps(
        zone_repo=AsyncMock(get_by_id=AsyncMock(return_value=zone)),
        alert_repo=AsyncMock(list=AsyncMock(return_value=[alert])),
        sensor_repo=AsyncMock(list=AsyncMock(return_value=[MagicMock()])),
        actuator_repo=AsyncMock(list=AsyncMock(return_value=[MagicMock()])),
        plant_batch_repo=AsyncMock(list_by_zone=AsyncMock(return_value=[batch])),
    )
    ctx = _ctx(deps)

    result = await get_zone_state(ctx, str(GROUP_ID), str(GREENHOUSE_ID), str(ZONE_ID))

    assert result["zone_id"] == str(ZONE_ID)
    assert result["name"] == "Zone A"
    assert result["sensor_count"] == 1
    assert result["actuator_count"] == 1
    assert len(result["plant_batches"]) == 1
    assert len(result["active_alerts"]) == 1


@pytest.mark.asyncio
async def test_get_zone_state_accepts_display_identifiers() -> None:
    """get_zone_state resolves simulator display identifiers before querying repos."""
    group = _make_group(name="group-001")
    greenhouse = _make_greenhouse(name="gh-001")
    zone = _make_zone(name="zone-01")
    deps = _make_deps(
        group_repo=AsyncMock(list=AsyncMock(return_value=[group])),
        greenhouse_repo=AsyncMock(list=AsyncMock(return_value=[greenhouse])),
        zone_repo=AsyncMock(
            list=AsyncMock(return_value=[zone]),
            get_by_id=AsyncMock(return_value=zone),
        ),
        alert_repo=AsyncMock(list=AsyncMock(return_value=[])),
        sensor_repo=AsyncMock(list=AsyncMock(return_value=[])),
        actuator_repo=AsyncMock(list=AsyncMock(return_value=[])),
        plant_batch_repo=AsyncMock(list_by_zone=AsyncMock(return_value=[])),
    )
    ctx = _ctx(deps)

    result = await get_zone_state(ctx, "group-001", "gh-001", "zone-01")

    assert result["zone_id"] == str(ZONE_ID)
    assert result["greenhouse_id"] == str(GREENHOUSE_ID)
    deps.zone_repo.get_by_id.assert_awaited_once_with(ZONE_ID)
    deps.alert_repo.list.assert_awaited_once_with(
        group_id=GROUP_ID,
        greenhouse_id=GREENHOUSE_ID,
        zone_id=ZONE_ID,
        status="active",
    )


@pytest.mark.asyncio
async def test_get_zone_state_accepts_mixed_uuid_and_display_identifiers() -> None:
    """get_zone_state resolves a selected UUID group with display greenhouse and zone IDs."""
    group = _make_group(name="group-001")
    greenhouse = _make_greenhouse(name="gh-001-tomatoes")
    zone = _make_zone(name="zone-01-seedlings")
    deps = _make_deps(
        group_repo=AsyncMock(
            get_by_id=AsyncMock(return_value=group),
            list=AsyncMock(return_value=[]),
        ),
        greenhouse_repo=AsyncMock(list=AsyncMock(return_value=[greenhouse])),
        zone_repo=AsyncMock(
            list=AsyncMock(return_value=[zone]),
            get_by_id=AsyncMock(return_value=zone),
        ),
        alert_repo=AsyncMock(list=AsyncMock(return_value=[])),
        sensor_repo=AsyncMock(list=AsyncMock(return_value=[])),
        actuator_repo=AsyncMock(list=AsyncMock(return_value=[])),
        plant_batch_repo=AsyncMock(list_by_zone=AsyncMock(return_value=[])),
    )
    ctx = _ctx(deps)

    result = await get_zone_state(ctx, str(GROUP_ID), "gh-001-tomatoes", "zone-01-seedlings")

    assert result["zone_id"] == str(ZONE_ID)
    deps.group_repo.get_by_id.assert_awaited_once_with(GROUP_ID)
    deps.greenhouse_repo.list.assert_awaited_once_with(group_id=GROUP_ID, name="gh-001-tomatoes")
    deps.zone_repo.list.assert_awaited_once_with(greenhouse_id=GREENHOUSE_ID, name="zone-01-seedlings")


@pytest.mark.asyncio
async def test_get_zone_state_not_found() -> None:
    """get_zone_state returns error dict when zone missing."""
    deps = _make_deps(zone_repo=AsyncMock(get_by_id=AsyncMock(return_value=None)))
    ctx = _ctx(deps)

    result = await get_zone_state(ctx, str(GROUP_ID), str(GREENHOUSE_ID), str(ZONE_ID))

    assert "error" in result


@pytest.mark.asyncio
async def test_get_zone_plant_info_returns_shape() -> None:
    """get_zone_plant_info returns plant batches with profile info."""
    zone = _make_zone()
    batch = _make_batch()
    profile = MagicMock()
    profile.id = uuid.uuid4()
    profile.crop_name = batch.species
    profile.growth_stage = batch.growth_stage
    profile.soil_moisture_min = 40.0
    profile.soil_moisture_opt = 55.0
    profile.soil_moisture_max = 70.0
    deps = _make_deps(
        zone_repo=AsyncMock(get_by_id=AsyncMock(return_value=zone)),
        plant_batch_repo=AsyncMock(list_by_zone=AsyncMock(return_value=[batch])),
        plant_profile_repo=AsyncMock(find_by_crop_and_stage=AsyncMock(return_value=profile)),
    )
    ctx = _ctx(deps)

    result = await get_zone_plant_info(ctx, str(GROUP_ID), str(GREENHOUSE_ID), str(ZONE_ID))

    assert result["zone_id"] == str(ZONE_ID)
    assert len(result["plant_batches"]) == 1
    pb = result["plant_batches"][0]
    assert "batch_id" in pb
    assert "name" in pb
    assert "species" in pb
    assert result["profiles"][0]["soil_moisture"] == {
        "min": 40.0,
        "optimal": 55.0,
        "max": 70.0,
    }
    assert result["profiles"][0]["soil_moisture_opt_missing"] is False


@pytest.mark.asyncio
async def test_get_zone_plant_info_reports_missing_soil_moisture_opt() -> None:
    """get_zone_plant_info flags missing optimal soil moisture thresholds."""
    zone = _make_zone()
    batch = _make_batch()
    profile = MagicMock()
    profile.id = uuid.uuid4()
    profile.crop_name = batch.species
    profile.growth_stage = batch.growth_stage
    profile.soil_moisture_min = 40.0
    profile.soil_moisture_opt = None
    profile.soil_moisture_max = 70.0
    deps = _make_deps(
        zone_repo=AsyncMock(get_by_id=AsyncMock(return_value=zone)),
        plant_batch_repo=AsyncMock(list_by_zone=AsyncMock(return_value=[batch])),
        plant_profile_repo=AsyncMock(find_by_crop_and_stage=AsyncMock(return_value=profile)),
    )
    ctx = _ctx(deps)

    result = await get_zone_plant_info(ctx, str(GROUP_ID), str(GREENHOUSE_ID), str(ZONE_ID))

    assert result["profiles"][0]["soil_moisture_opt_missing"] is True
    assert result["profiles"][0]["soil_moisture"]["optimal"] is None


@pytest.mark.asyncio
async def test_get_zone_plant_info_reports_missing_profile() -> None:
    """get_zone_plant_info reports missing profile without failing."""
    zone = _make_zone()
    batch = _make_batch()
    deps = _make_deps(
        zone_repo=AsyncMock(get_by_id=AsyncMock(return_value=zone)),
        plant_batch_repo=AsyncMock(list_by_zone=AsyncMock(return_value=[batch])),
        plant_profile_repo=AsyncMock(find_by_crop_and_stage=AsyncMock(return_value=None)),
    )
    ctx = _ctx(deps)

    result = await get_zone_plant_info(ctx, str(GROUP_ID), str(GREENHOUSE_ID), str(ZONE_ID))

    assert result["profiles"][0]["profile_found"] is False
    assert result["profiles"][0]["soil_moisture_opt_missing"] is True


@pytest.mark.asyncio
async def test_get_zone_plant_info_prefers_linked_profile() -> None:
    """get_zone_plant_info uses profile_id before species/stage matching."""
    zone = _make_zone()
    linked_profile_id = uuid.uuid4()
    batch = _make_batch(profile_id=linked_profile_id, species="Tomato", growth_stage="seedling")
    linked_profile = MagicMock()
    linked_profile.id = linked_profile_id
    linked_profile.crop_name = "Cucumber"
    linked_profile.growth_stage = "vegetative"
    linked_profile.soil_moisture_min = 45.0
    linked_profile.soil_moisture_opt = 60.0
    linked_profile.soil_moisture_max = 75.0
    matched_profile = MagicMock()
    matched_profile.id = uuid.uuid4()

    deps = _make_deps(
        zone_repo=AsyncMock(get_by_id=AsyncMock(return_value=zone)),
        plant_batch_repo=AsyncMock(list_by_zone=AsyncMock(return_value=[batch])),
        plant_profile_repo=AsyncMock(
            get_by_id=AsyncMock(return_value=linked_profile),
            find_by_crop_and_stage=AsyncMock(return_value=matched_profile),
        ),
    )
    ctx = _ctx(deps)

    result = await get_zone_plant_info(ctx, str(GROUP_ID), str(GREENHOUSE_ID), str(ZONE_ID))

    profile = result["profiles"][0]
    assert profile["profile_id"] == str(linked_profile_id)
    assert profile["profile_source"] == "linked_profile"
    assert profile["crop_name"] == "Cucumber"
    deps.plant_profile_repo.find_by_crop_and_stage.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_zone_plant_info_falls_back_when_linked_profile_missing() -> None:
    """get_zone_plant_info reports dangling link and still uses matching profile."""
    zone = _make_zone()
    linked_profile_id = uuid.uuid4()
    fallback_profile = MagicMock()
    fallback_profile.id = uuid.uuid4()
    fallback_profile.crop_name = "Tomato"
    fallback_profile.growth_stage = "seedling"
    fallback_profile.soil_moisture_min = 40.0
    fallback_profile.soil_moisture_opt = 55.0
    fallback_profile.soil_moisture_max = 70.0
    batch = _make_batch(profile_id=linked_profile_id, species="Tomato", growth_stage="seedling")
    deps = _make_deps(
        zone_repo=AsyncMock(get_by_id=AsyncMock(return_value=zone)),
        plant_batch_repo=AsyncMock(list_by_zone=AsyncMock(return_value=[batch])),
        plant_profile_repo=AsyncMock(
            get_by_id=AsyncMock(return_value=None),
            find_by_crop_and_stage=AsyncMock(return_value=fallback_profile),
        ),
    )
    ctx = _ctx(deps)

    result = await get_zone_plant_info(ctx, str(GROUP_ID), str(GREENHOUSE_ID), str(ZONE_ID))

    profile = result["profiles"][0]
    assert profile["profile_id"] == str(fallback_profile.id)
    assert profile["profile_source"] == "species_growth_stage_match"
    assert profile["linked_profile_missing"] is True


@pytest.mark.asyncio
async def test_get_zone_plant_info_no_batches() -> None:
    """get_zone_plant_info returns empty plant_batches when zone has none."""
    zone = _make_zone()
    deps = _make_deps(
        zone_repo=AsyncMock(get_by_id=AsyncMock(return_value=zone)),
        plant_batch_repo=AsyncMock(list_by_zone=AsyncMock(return_value=[])),
    )
    ctx = _ctx(deps)

    result = await get_zone_plant_info(ctx, str(GROUP_ID), str(GREENHOUSE_ID), str(ZONE_ID))

    assert result["plant_batches"] == []


# ---------------------------------------------------------------------------
# Plant tools
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_plant_batches_returns_shape() -> None:
    """get_plant_batches walks greenhouses and zones, returns batch dicts."""
    gh = _make_greenhouse()
    zone = _make_zone()
    batch = _make_batch()
    deps = _make_deps(
        greenhouse_repo=AsyncMock(list=AsyncMock(return_value=[gh])),
        zone_repo=AsyncMock(list=AsyncMock(return_value=[zone])),
        plant_batch_repo=AsyncMock(list_by_zone=AsyncMock(return_value=[batch])),
    )
    ctx = _ctx(deps)

    result = await get_plant_batches(ctx, str(GROUP_ID))

    assert isinstance(result, list)
    assert len(result) == 1
    entry = result[0]
    assert "batch_id" in entry
    assert "greenhouse_id" in entry
    assert "zone_id" in entry


@pytest.mark.asyncio
async def test_get_plant_profile_returns_shape() -> None:
    """get_plant_profile returns profile with threshold ranges."""
    profile = MagicMock()
    profile.id = uuid.uuid4()
    profile.crop_name = "Tomato"
    profile.growth_stage = "flowering"
    profile.temp_min = 18.0
    profile.temp_opt = 24.0
    profile.temp_max = 30.0
    profile.humidity_min = 50.0
    profile.humidity_opt = 65.0
    profile.humidity_max = 80.0
    profile.soil_moisture_min = 40.0
    profile.soil_moisture_opt = 60.0
    profile.soil_moisture_max = 80.0
    profile.co2_min = 400.0
    profile.co2_opt = 800.0
    profile.co2_max = 1200.0
    profile.light_min = 200.0
    profile.light_opt = 500.0
    profile.light_max = 800.0
    profile.description = "Ideal for fruiting tomatoes"

    deps = _make_deps(
        plant_profile_repo=AsyncMock(get_by_id=AsyncMock(return_value=profile)),
    )
    ctx = _ctx(deps)

    result = await get_plant_profile(ctx, str(profile.id))

    assert result["profile_id"] == str(profile.id)
    assert result["crop_name"] == "Tomato"
    assert result["temperature"]["min"] == 18.0
    assert result["temperature"]["optimal"] == 24.0
    assert result["temperature"]["max"] == 30.0
    assert result["humidity"]["optimal"] == 65.0
    assert result["co2"]["optimal"] == 800.0


@pytest.mark.asyncio
async def test_get_plant_profile_not_found() -> None:
    """get_plant_profile returns error when profile missing."""
    deps = _make_deps(
        plant_profile_repo=AsyncMock(get_by_id=AsyncMock(return_value=None)),
    )
    ctx = _ctx(deps)

    result = await get_plant_profile(ctx, str(uuid.uuid4()))

    assert "error" in result


# ---------------------------------------------------------------------------
# Telemetry tools
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_today_group_summary_delegates() -> None:
    """get_today_group_summary delegates to telemetry_repo.get_group_summary."""
    fake_summary = [{"metric": "temperature", "min": 18.0, "max": 30.0, "latest": 24.5}]
    telemetry_repo = MagicMock()
    telemetry_repo.get_group_summary.return_value = fake_summary
    deps = _make_deps(telemetry_repo=telemetry_repo)
    ctx = _ctx(deps)

    result = await get_today_group_summary(ctx, str(GROUP_ID))

    assert result == fake_summary
    telemetry_repo.get_group_summary.assert_called_once_with(str(GROUP_ID))


@pytest.mark.asyncio
async def test_get_today_greenhouse_summary_delegates() -> None:
    """get_today_greenhouse_summary delegates to telemetry_repo.get_greenhouse_summary."""
    fake_summary = [{"metric": "humidity", "min": 50.0, "max": 80.0, "latest": 65.0}]
    telemetry_repo = MagicMock()
    telemetry_repo.get_greenhouse_summary.return_value = fake_summary
    deps = _make_deps(telemetry_repo=telemetry_repo)
    ctx = _ctx(deps)

    result = await get_today_greenhouse_summary(ctx, str(GROUP_ID), str(GREENHOUSE_ID))

    assert result == fake_summary
    telemetry_repo.get_greenhouse_summary.assert_called_once_with(
        str(GROUP_ID), str(GREENHOUSE_ID),
    )


@pytest.mark.asyncio
async def test_get_today_zone_summary_delegates() -> None:
    """get_today_zone_summary delegates to telemetry_repo.get_zone_summary."""
    fake_summary = [{"metric": "soil_moisture", "min": 30.0, "max": 70.0, "latest": 55.0}]
    telemetry_repo = MagicMock()
    telemetry_repo.get_zone_summary.return_value = fake_summary
    deps = _make_deps(telemetry_repo=telemetry_repo)
    ctx = _ctx(deps)

    result = await get_today_zone_summary(
        ctx, str(GROUP_ID), str(GREENHOUSE_ID), str(ZONE_ID),
    )

    assert result == fake_summary
    telemetry_repo.get_zone_summary.assert_called_once_with(
        str(GROUP_ID), str(GREENHOUSE_ID), str(ZONE_ID),
    )


@pytest.mark.asyncio
async def test_get_latest_readings_delegates() -> None:
    """get_latest_readings delegates to telemetry_repo.get_latest."""
    fake_readings = [{"metric": "temperature", "_value": 24.5}]
    telemetry_repo = MagicMock()
    telemetry_repo.get_latest.return_value = fake_readings
    deps = _make_deps(telemetry_repo=telemetry_repo)
    ctx = _ctx(deps)

    result = await get_latest_readings(ctx, str(GROUP_ID))

    assert result == fake_readings
    telemetry_repo.get_latest.assert_called_once_with(str(GROUP_ID), greenhouse_id=None, zone_id=None)


@pytest.mark.asyncio
async def test_get_latest_readings_with_filters() -> None:
    """get_latest_readings passes greenhouse_id and zone_id to repo."""
    telemetry_repo = MagicMock()
    telemetry_repo.get_latest.return_value = []
    deps = _make_deps(telemetry_repo=telemetry_repo)
    ctx = _ctx(deps)

    await get_latest_readings(
        ctx, str(GROUP_ID),
        greenhouse_id=str(GREENHOUSE_ID),
        zone_id=str(ZONE_ID),
    )

    telemetry_repo.get_latest.assert_called_once_with(
        str(GROUP_ID), greenhouse_id=str(GREENHOUSE_ID), zone_id=str(ZONE_ID),
    )


@pytest.mark.asyncio
async def test_get_latest_readings_resolves_mixed_scope_identifiers() -> None:
    """get_latest_readings resolves selected UUID group with display greenhouse and zone IDs."""
    group = _make_group(name="group-001")
    greenhouse = _make_greenhouse(name="gh-001-tomatoes")
    zone = _make_zone(name="zone-01-seedlings")
    telemetry_repo = MagicMock()
    telemetry_repo.get_latest.return_value = [{"metric": "soil_moisture", "_value": 42.0}]
    deps = _make_deps(
        group_repo=AsyncMock(get_by_id=AsyncMock(return_value=group)),
        greenhouse_repo=AsyncMock(list=AsyncMock(return_value=[greenhouse])),
        zone_repo=AsyncMock(list=AsyncMock(return_value=[zone])),
        telemetry_repo=telemetry_repo,
    )
    ctx = _ctx(deps)

    result = await get_latest_readings(
        ctx,
        str(GROUP_ID),
        greenhouse_id="gh-001-tomatoes",
        zone_id="zone-01-seedlings",
    )

    assert result == [{"metric": "soil_moisture", "_value": 42.0}]
    telemetry_repo.get_latest.assert_called_once_with(
        str(GROUP_ID), greenhouse_id=str(GREENHOUSE_ID), zone_id=str(ZONE_ID),
    )


# ---------------------------------------------------------------------------
# Alert tools
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_active_alerts_returns_shape() -> None:
    """get_active_alerts returns list of alert dicts."""
    alert = _make_alert()
    deps = _make_deps(
        alert_repo=AsyncMock(list=AsyncMock(return_value=[alert])),
    )
    ctx = _ctx(deps)

    result = await get_active_alerts(ctx, str(GROUP_ID))

    assert isinstance(result, list)
    assert len(result) == 1
    entry = result[0]
    assert entry["alert_id"] == str(alert.id)
    assert entry["severity"] == "warning"
    assert "status" not in entry  # Not included in output
    assert "created_at" in entry


@pytest.mark.asyncio
async def test_get_active_alerts_filters_by_scope() -> None:
    """get_active_alerts passes greenhouse_id and zone_id to repo."""
    alert_repo = AsyncMock()
    alert_repo.list = AsyncMock(return_value=[])
    deps = _make_deps(alert_repo=alert_repo)
    ctx = _ctx(deps)

    await get_active_alerts(
        ctx, str(GROUP_ID),
        greenhouse_id=str(GREENHOUSE_ID),
        zone_id=str(ZONE_ID),
    )

    alert_repo.list.assert_called_once_with(
        group_id=GROUP_ID,
        status="active",
        greenhouse_id=GREENHOUSE_ID,
        zone_id=ZONE_ID,
    )


@pytest.mark.asyncio
async def test_get_active_alerts_empty() -> None:
    """get_active_alerts returns empty list when no alerts."""
    deps = _make_deps(alert_repo=AsyncMock(list=AsyncMock(return_value=[])))
    ctx = _ctx(deps)

    result = await get_active_alerts(ctx, str(GROUP_ID))

    assert result == []


# ---------------------------------------------------------------------------
# Command tools
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_recent_commands_returns_shape() -> None:
    """get_recent_commands returns list of command dicts."""
    cmd = _make_command()
    deps = _make_deps(
        command_repo=AsyncMock(get_recent=AsyncMock(return_value=[cmd])),
    )
    ctx = _ctx(deps)

    result = await get_recent_commands(ctx, str(GROUP_ID))

    assert isinstance(result, list)
    assert len(result) == 1
    entry = result[0]
    assert entry["command_id"] == str(cmd.id)
    assert entry["actuator"] == "pump"
    assert entry["action"] == "on"
    assert entry["status"] == "executed"
    assert "created_at" in entry


@pytest.mark.asyncio
async def test_get_recent_commands_filters_by_scope() -> None:
    """get_recent_commands passes filters to repo."""
    command_repo = AsyncMock()
    command_repo.get_recent = AsyncMock(return_value=[])
    deps = _make_deps(command_repo=command_repo)
    ctx = _ctx(deps)

    await get_recent_commands(
        ctx, str(GROUP_ID),
        greenhouse_id=str(GREENHOUSE_ID),
        zone_id=str(ZONE_ID),
    )

    command_repo.get_recent.assert_called_once_with(
        group_id=GROUP_ID,
        greenhouse_id=GREENHOUSE_ID,
        zone_id=ZONE_ID,
    )


@pytest.mark.asyncio
async def test_get_recent_commands_empty() -> None:
    """get_recent_commands returns empty list when no commands."""
    deps = _make_deps(command_repo=AsyncMock(get_recent=AsyncMock(return_value=[])))
    ctx = _ctx(deps)

    result = await get_recent_commands(ctx, str(GROUP_ID))

    assert result == []


# ---------------------------------------------------------------------------
# Tool registration on agent
# ---------------------------------------------------------------------------

def test_all_tools_list_has_expected_count() -> None:
    """ALL_TOOLS should contain read-only and approval-required proposal tools."""
    from app.services.ai_agent.tools import ALL_TOOLS
    assert len(ALL_TOOLS) == 19


def test_all_tools_are_callable() -> None:
    """Every entry in ALL_TOOLS must be callable."""
    from app.services.ai_agent.tools import ALL_TOOLS
    for tool_func in ALL_TOOLS:
        assert callable(tool_func), f"{tool_func.__name__} is not callable"
