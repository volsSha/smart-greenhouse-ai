"""Device registry CRUD endpoints for edge nodes, sensors, and actuators."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.repositories.device_repository import (
    ActuatorRepository,
    EdgeNodeRepository,
    SensorRepository,
)
from app.schemas.plant_batches import (
    ActuatorCreate,
    ActuatorResponse,
    EdgeNodeCreate,
    EdgeNodeResponse,
    SensorCreate,
    SensorResponse,
)

router = APIRouter(
    prefix="/api/groups/{group_id}/devices",
    tags=["devices"],
)


# ---------------------------------------------------------------------------
# Edge Node endpoints
# ---------------------------------------------------------------------------


@router.get("/edge-nodes", response_model=list[EdgeNodeResponse])
async def list_edge_nodes(
    group_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[EdgeNodeResponse]:
    """List all edge nodes in a group.

    Since edge nodes belong to greenhouses, we return all edge nodes
    across all greenhouses in the group.
    """
    from app.repositories.greenhouse_repository import GreenhouseRepository

    gh_repo = GreenhouseRepository(session)
    greenhouses = await gh_repo.list(group_id=group_id)
    gh_ids = [gh.id for gh in greenhouses]

    repo = EdgeNodeRepository(session)
    all_nodes: list[EdgeNodeResponse] = []
    for gh_id in gh_ids:
        nodes = await repo.list(greenhouse_id=gh_id)
        all_nodes.extend(EdgeNodeResponse.model_validate(n) for n in nodes)
    return all_nodes


@router.post("/edge-nodes", response_model=EdgeNodeResponse, status_code=201)
async def create_edge_node(
    group_id: UUID,
    body: EdgeNodeCreate,
    session: AsyncSession = Depends(get_db_session),
) -> EdgeNodeResponse:
    """Register a new edge node."""
    from app.repositories.greenhouse_repository import GreenhouseRepository

    # Verify greenhouse belongs to the group
    gh_repo = GreenhouseRepository(session)
    greenhouse = await gh_repo.get_by_id(body.greenhouse_id)
    if greenhouse is None or greenhouse.group_id != group_id:
        raise HTTPException(status_code=404, detail="Greenhouse not found")

    repo = EdgeNodeRepository(session)
    node = await repo.create(
        greenhouse_id=body.greenhouse_id,
        node_key=body.node_key,
        name=body.name,
        node_type=body.node_type,
        firmware_version=body.firmware_version,
        mqtt_username=body.mqtt_username,
        mqtt_token=body.mqtt_token,
    )
    await session.commit()
    return EdgeNodeResponse.model_validate(node)


# ---------------------------------------------------------------------------
# Sensor endpoints
# ---------------------------------------------------------------------------


@router.get("/sensors", response_model=list[SensorResponse])
async def list_sensors(
    group_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[SensorResponse]:
    """List all sensors in a group."""
    from app.repositories.greenhouse_repository import GreenhouseRepository
    from app.repositories.zone_repository import ZoneRepository

    gh_repo = GreenhouseRepository(session)
    greenhouses = await gh_repo.list(group_id=group_id)
    gh_ids = [gh.id for gh in greenhouses]

    zone_repo = ZoneRepository(session)
    all_sensors: list[SensorResponse] = []
    for gh_id in gh_ids:
        zones = await zone_repo.list(greenhouse_id=gh_id)
        for zone in zones:
            repo = SensorRepository(session)
            sensors = await repo.list(zone_id=zone.id)
            all_sensors.extend(SensorResponse.model_validate(s) for s in sensors)
    return all_sensors


@router.post("/sensors", response_model=SensorResponse, status_code=201)
async def create_sensor(
    group_id: UUID,
    body: SensorCreate,
    session: AsyncSession = Depends(get_db_session),
) -> SensorResponse:
    """Register a new sensor."""
    from app.repositories.greenhouse_repository import GreenhouseRepository
    from app.repositories.zone_repository import ZoneRepository

    # Verify zone belongs to a greenhouse in the group
    zone_repo = ZoneRepository(session)
    zone = await zone_repo.get_by_id(body.zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")

    gh_repo = GreenhouseRepository(session)
    greenhouse = await gh_repo.get_by_id(zone.greenhouse_id)
    if greenhouse is None or greenhouse.group_id != group_id:
        raise HTTPException(status_code=404, detail="Zone not found in this group")

    repo = SensorRepository(session)
    sensor = await repo.create(
        zone_id=body.zone_id,
        sensor_key=body.sensor_key,
        metric=body.metric,
        unit=body.unit,
        edge_node_id=body.edge_node_id,
        is_active=body.is_active,
    )
    return SensorResponse.model_validate(sensor)


# ---------------------------------------------------------------------------
# Actuator endpoints
# ---------------------------------------------------------------------------


@router.get("/actuators", response_model=list[ActuatorResponse])
async def list_actuators(
    group_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[ActuatorResponse]:
    """List all actuators in a group."""
    from app.repositories.greenhouse_repository import GreenhouseRepository
    from app.repositories.zone_repository import ZoneRepository

    gh_repo = GreenhouseRepository(session)
    greenhouses = await gh_repo.list(group_id=group_id)
    gh_ids = [gh.id for gh in greenhouses]

    zone_repo = ZoneRepository(session)
    all_actuators: list[ActuatorResponse] = []
    for gh_id in gh_ids:
        zones = await zone_repo.list(greenhouse_id=gh_id)
        for zone in zones:
            repo = ActuatorRepository(session)
            actuators = await repo.list(zone_id=zone.id)
            all_actuators.extend(
                ActuatorResponse.model_validate(a) for a in actuators
            )
    return all_actuators


@router.post("/actuators", response_model=ActuatorResponse, status_code=201)
async def create_actuator(
    group_id: UUID,
    body: ActuatorCreate,
    session: AsyncSession = Depends(get_db_session),
) -> ActuatorResponse:
    """Register a new actuator."""
    from app.repositories.greenhouse_repository import GreenhouseRepository
    from app.repositories.zone_repository import ZoneRepository

    # Verify zone belongs to a greenhouse in the group
    zone_repo = ZoneRepository(session)
    zone = await zone_repo.get_by_id(body.zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")

    gh_repo = GreenhouseRepository(session)
    greenhouse = await gh_repo.get_by_id(zone.greenhouse_id)
    if greenhouse is None or greenhouse.group_id != group_id:
        raise HTTPException(status_code=404, detail="Zone not found in this group")

    repo = ActuatorRepository(session)
    actuator = await repo.create(
        zone_id=body.zone_id,
        actuator_key=body.actuator_key,
        actuator_type=body.actuator_type,
        edge_node_id=body.edge_node_id,
        is_active=body.is_active,
    )
    return ActuatorResponse.model_validate(actuator)
