"""Dependency container for AI tool functions.

Each tool receives a ``RunContext[ToolDeps]`` that provides access to all
repositories and services the tools need.  The ``GreenhouseAIAgent`` builds
a ``ToolDeps`` instance from the current ``AsyncSession`` and passes it as
the agent's ``deps`` value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.repositories.alert_repository import AlertRepository
    from app.repositories.command_repository import CommandRepository
    from app.repositories.device_repository import ActuatorRepository, SensorRepository
    from app.repositories.greenhouse_repository import GreenhouseRepository
    from app.repositories.group_repository import GroupRepository
    from app.repositories.plant_batch_repository import (
        PlantBatchRepository,
        PlantProfileRepository,
    )
    from app.repositories.rag_repository import RAGRepository
    from app.repositories.telemetry_repository import TelemetryRepository
    from app.repositories.zone_repository import ZoneRepository
    from app.services.ai_agent.tool_logging import ToolCallLogger
    from app.config import Settings


@dataclass
class ToolDeps:
    """Repository and service dependencies injected into AI tool functions."""

    group_repo: GroupRepository = field(repr=False)
    greenhouse_repo: GreenhouseRepository = field(repr=False)
    zone_repo: ZoneRepository = field(repr=False)
    alert_repo: AlertRepository = field(repr=False)
    command_repo: CommandRepository = field(repr=False)
    plant_batch_repo: PlantBatchRepository = field(repr=False)
    plant_profile_repo: PlantProfileRepository = field(repr=False)
    telemetry_repo: TelemetryRepository = field(repr=False)
    sensor_repo: SensorRepository = field(repr=False)
    actuator_repo: ActuatorRepository = field(repr=False)
    tool_logger: ToolCallLogger = field(repr=False)
    rag_repo: RAGRepository | None = field(default=None, repr=False)
    settings: Settings | None = field(default=None, repr=False)
