"""Mode-aware command execution routing.

Dispatches approved commands to the correct execution backend based
on the command's ``mode`` field:

- ``simulator`` — apply to :class:`SimulatedZoneState` (in-memory)
- ``mqtt`` — signal that the caller should use the MQTT publisher
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.models.command import CommandLog
from app.services.simulator.zone_state import SimulatedZoneState

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ModeRouter:
    """Routes command execution to the correct backend based on mode."""

    def __init__(self, sim_state: SimulatedZoneState | None = None) -> None:
        self._sim_state = sim_state

    async def route(self, command: CommandLog, session: AsyncSession) -> dict[str, Any]:
        """Dispatch *command* to the appropriate execution backend.

        Returns a result dict the caller uses to determine next steps.
        For simulator mode: the command is applied and a result dict with
        ``applied=True`` is returned.
        For mqtt mode: a result dict with ``needs_publish=True`` is returned
        so the caller falls through to the MQTT publisher.

        Raises ``CommandError`` on failures.
        """
        if command.mode == "simulator":
            return await self._route_simulator(command, session)
        return {"mode": "mqtt", "needs_publish": True}

    async def _route_simulator(
        self, command: CommandLog, session: AsyncSession
    ) -> dict[str, Any]:
        if self._sim_state is None or not self._sim_state.is_initialized:
            from app.services.command_service import CommandError

            raise CommandError("Simulator is not running — start the simulator first")

        group_id = str(command.group_id)
        greenhouse_id = str(command.greenhouse_id)
        zone_id = str(command.zone_id)
        if await self._sim_state.get_state(group_id, greenhouse_id, zone_id) is None:
            from app.models.greenhouse import Greenhouse
            from app.models.group import GreenhouseGroup
            from app.models.zone import GreenhouseZone

            group = await session.get(GreenhouseGroup, command.group_id)
            greenhouse = await session.get(Greenhouse, command.greenhouse_id)
            zone = await session.get(GreenhouseZone, command.zone_id)
            if group is not None and greenhouse is not None and zone is not None:
                group_id = group.name
                greenhouse_id = greenhouse.name
                zone_id = zone.name

        cmd_dict: dict[str, Any] = {
            "group_id": group_id,
            "greenhouse_id": greenhouse_id,
            "zone_id": zone_id,
            "actuator_name": command.actuator_name,
            "action": command.action,
            "value": command.value or 0.0,
            "duration_seconds": command.duration_seconds,
            "source": command.source,
        }

        await self._sim_state.apply_command(cmd_dict)
        logger.info(
            "Routed command %s to simulator: %s %s on %s/%s/%s",
            command.id,
            command.actuator_name,
            command.action,
            group_id,
            greenhouse_id,
            zone_id,
        )
        return {"mode": "simulator", "applied": True}
