"""Database provisioning for simulator-managed greenhouse topology."""

from __future__ import annotations

from dataclasses import dataclass
from secrets import token_urlsafe

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.device_repository import ActuatorRepository, EdgeNodeRepository, SensorRepository
from app.repositories.greenhouse_repository import GreenhouseRepository
from app.repositories.group_repository import GroupRepository
from app.repositories.plant_batch_repository import PlantBatchRepository
from app.repositories.zone_repository import ZoneRepository
from app.services.simulator.zone_state import (
    simulator_greenhouse_id,
    simulator_group_id,
    simulator_zone_id,
)

SENSOR_DEFINITIONS = (
    ("temperature", "temperature", "celsius"),
    ("air_humidity", "air_humidity", "%"),
    ("soil_moisture", "soil_moisture", "%"),
    ("co2", "co2", "ppm"),
    ("light", "light", "lux"),
)
ACTUATOR_TYPES = ("pump", "fan", "heater", "lamp")


@dataclass(frozen=True)
class ProvisionedZone:
    group_id: str
    greenhouse_id: str
    zone_id: str


async def provision_simulator_topology(
    session: AsyncSession,
    *,
    groups: int,
    greenhouses_per_group: int,
    zones_per_greenhouse: int,
) -> list[ProvisionedZone]:
    group_repo = GroupRepository(session)
    greenhouse_repo = GreenhouseRepository(session)
    zone_repo = ZoneRepository(session)
    edge_repo = EdgeNodeRepository(session)
    sensor_repo = SensorRepository(session)
    actuator_repo = ActuatorRepository(session)
    plant_repo = PlantBatchRepository(session)
    provisioned: list[ProvisionedZone] = []

    for group_index in range(1, groups + 1):
        group_name = simulator_group_id(group_index)
        group = await _first_by_name(await group_repo.list(), group_name)
        if group is None:
            group = await group_repo.create(
                name=group_name,
                location="Internal simulator",
                description="Simulator-managed greenhouse group",
            )

        for greenhouse_index in range(1, greenhouses_per_group + 1):
            greenhouse_name = simulator_greenhouse_id(greenhouse_index)
            greenhouses = await greenhouse_repo.list(group_id=group.id)
            greenhouse = await _first_by_name(greenhouses, greenhouse_name)
            if greenhouse is None:
                greenhouse = await greenhouse_repo.create(
                    group_id=group.id,
                    name=greenhouse_name,
                    location="Internal simulator",
                    description="Simulator-managed greenhouse",
                )

            for zone_index in range(1, zones_per_greenhouse + 1):
                zone_name = simulator_zone_id(zone_index)
                zones = await zone_repo.list(greenhouse_id=greenhouse.id)
                zone = await _first_by_name(zones, zone_name)
                if zone is None:
                    zone = await zone_repo.create(
                        greenhouse_id=greenhouse.id,
                        name=zone_name,
                        description="Simulator-managed zone",
                        source_type="simulator",
                        simulator_managed=True,
                    )
                else:
                    await zone_repo.update(zone.id, source_type="simulator", simulator_managed=True)

                node_key = f"sim-{zone.id}"
                edge_node = await edge_repo.get_by_node_key(node_key)
                if edge_node is None:
                    edge_node = await edge_repo.create(
                        greenhouse_id=greenhouse.id,
                        node_key=node_key,
                        name=f"Simulator node {zone.name}",
                        node_type="simulator",
                        mqtt_username=node_key,
                        mqtt_token=token_urlsafe(24),
                    )

                sensors = await sensor_repo.list(zone_id=zone.id)
                sensor_keys = {sensor.sensor_key for sensor in sensors}
                for key, metric, unit in SENSOR_DEFINITIONS:
                    if key not in sensor_keys:
                        await sensor_repo.create(
                            zone_id=zone.id,
                            edge_node_id=edge_node.id,
                            sensor_key=key,
                            metric=metric,
                            unit=unit,
                        )

                actuators = await actuator_repo.list(zone_id=zone.id)
                actuator_keys = {actuator.actuator_key for actuator in actuators}
                for actuator_type in ACTUATOR_TYPES:
                    if actuator_type not in actuator_keys:
                        await actuator_repo.create(
                            zone_id=zone.id,
                            edge_node_id=edge_node.id,
                            actuator_key=actuator_type,
                            actuator_type=actuator_type,
                        )

                plant_batches = await plant_repo.list_by_zone(zone.id)
                if not plant_batches:
                    await plant_repo.create(
                        zone_id=zone.id,
                        name=f"Simulator plants {zone_index}",
                        species="Mixed greenhouse crop",
                        growth_stage="vegetative",
                        notes="Created with simulator topology",
                    )

                provisioned.append(
                    ProvisionedZone(
                        group_id=str(group.id),
                        greenhouse_id=str(greenhouse.id),
                        zone_id=str(zone.id),
                    )
                )

    await session.commit()
    return provisioned


async def _first_by_name(items, name: str):
    return next((item for item in items if item.name == name), None)
