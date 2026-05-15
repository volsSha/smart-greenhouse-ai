"""In-memory simulated zone state for the internal simulator mode.

Holds mutable actuator states per zone with timestamped activations
so telemetry generation can reflect the effect of approved commands
(e.g. rising soil moisture while a pump is running).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

GROUP_LABELS = (
    "vegetable-production",
    "herb-nursery",
    "fruit-crops",
    "research-trials",
    "seedling-starts",
    "flower-production",
    "organic-farm",
    "hydroponic-range",
    "climate-lab",
    "market-garden",
)

GREENHOUSE_LABELS = (
    "tomatoes",
    "cucumbers",
    "bell-peppers",
    "lettuce",
    "strawberries",
    "basil",
    "spinach",
    "microgreens",
    "eggplants",
    "cherry-tomatoes",
    "herbs",
    "peppers",
    "kale",
    "mint",
    "arugula",
    "seedlings",
    "flowers",
    "melons",
    "beans",
    "experimental-crops",
)

ZONE_LABELS = (
    "seedlings",
    "vegetative-growth",
    "flowering",
    "fruiting",
    "propagation",
    "irrigation-test",
    "high-light-bed",
    "shade-bed",
    "nutrient-trial",
    "harvest-ready",
    "cool-zone",
    "warm-zone",
    "humidity-control",
    "co2-enrichment",
    "soil-moisture-test",
    "young-plants",
    "mature-plants",
    "quarantine",
    "pollination",
    "storage-bench",
)


def simulator_group_id(index: int) -> str:
    return f"group-{index:03d}-{GROUP_LABELS[(index - 1) % len(GROUP_LABELS)]}"


def simulator_greenhouse_id(index: int) -> str:
    return f"gh-{index:03d}-{GREENHOUSE_LABELS[(index - 1) % len(GREENHOUSE_LABELS)]}"


def simulator_zone_id(index: int) -> str:
    return f"zone-{index:02d}-{ZONE_LABELS[(index - 1) % len(ZONE_LABELS)]}"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class ActuatorState:
    """Current state of a single actuator within a simulated zone."""

    active: bool = False
    value: float = 0.0
    activated_at: datetime | None = None
    duration_seconds: int | None = None  # None = indefinite


@dataclass
class ZoneState:
    """All mutable state for one simulated zone."""

    group_id: str
    greenhouse_id: str
    zone_id: str

    # Metric baselines (modified by scenarios and actuator effects)
    temperature: float = 24.0
    air_humidity: float = 60.0
    soil_moisture: float = 55.0
    co2: float = 850.0
    light: float = 500.0

    # Actuator states
    pump: ActuatorState = field(default_factory=ActuatorState)
    fan: ActuatorState = field(default_factory=ActuatorState)
    heater: ActuatorState = field(default_factory=ActuatorState)
    lamp: ActuatorState = field(default_factory=ActuatorState)

    def actuator_states(self) -> dict[str, dict[str, Any]]:
        """Return a dict of actuator states for API serialization."""
        return {
            "pump": {
                "active": self.pump.active,
                "value": self.pump.value,
                "remaining_seconds": self._remaining(self.pump),
            },
            "fan": {
                "active": self.fan.active,
                "value": self.fan.value,
                "remaining_seconds": self._remaining(self.fan),
            },
            "heater": {
                "active": self.heater.active,
                "value": self.heater.value,
                "remaining_seconds": self._remaining(self.heater),
            },
            "lamp": {
                "active": self.lamp.active,
                "value": self.lamp.value,
                "remaining_seconds": self._remaining(self.lamp),
            },
        }

    def animation_flags(self) -> dict[str, bool]:
        """Return which animations should be playing."""
        return {k: v["active"] for k, v in self.actuator_states().items()}

    @staticmethod
    def _remaining(act: ActuatorState) -> float | None:
        if not act.active or act.activated_at is None or act.duration_seconds is None:
            return None
        elapsed = (datetime.now(timezone.utc) - act.activated_at).total_seconds()
        remaining = act.duration_seconds - elapsed
        return max(0.0, remaining)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SimulatedZoneState:
    """In-memory mutable state for all simulated zones.

    This is a single-instance service. One instance is created per
    simulator session and reset on stop. All mutations use an
    ``asyncio.Lock`` to prevent torn reads between the background
    telemetry task and API-triggered command mutations.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._zones: dict[tuple[str, str, str], ZoneState] = {}
        self._initialized = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(
        self,
        num_groups: int,
        greenhouses_per_group: int,
        zones_per_greenhouse: int,
        scenario: str = "normal",
    ) -> None:
        """Build zone topology and apply scenario baselines."""
        self._zones.clear()
        scenario_offsets = self._scenario_offsets(scenario)

        for g in range(1, num_groups + 1):
            group_id = simulator_group_id(g)
            for gh in range(1, greenhouses_per_group + 1):
                greenhouse_id = simulator_greenhouse_id(gh)
                for z in range(1, zones_per_greenhouse + 1):
                    zone_id = simulator_zone_id(z)
                    key = (group_id, greenhouse_id, zone_id)
                    base_metrics = self._base_metrics()
                    for metric in base_metrics:
                        offset = scenario_offsets.get(metric, 0.0)
                        base_metrics[metric] += offset + g + gh + z
                    self._zones[key] = ZoneState(
                        group_id=group_id,
                        greenhouse_id=greenhouse_id,
                        zone_id=zone_id,
                        **base_metrics,
                    )
        self._initialized = True

    def reset(self) -> None:
        """Clear all zone state (called on simulator stop)."""
        self._zones.clear()
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    # ------------------------------------------------------------------
    # Command application
    # ------------------------------------------------------------------

    async def apply_command(self, command: dict[str, Any]) -> None:
        """Apply an actuator command to the appropriate zone state.

        Args:
            command: Dict with keys ``group_id``, ``greenhouse_id``,
                ``zone_id``, ``actuator_name``, ``action``, ``value``,
                ``duration_seconds``, ``source``.
        """
        key = (
            command.get("group_id", ""),
            command.get("greenhouse_id", ""),
            command.get("zone_id", ""),
        )
        if key not in self._zones:
            logger.warning("apply_command called for unknown zone: %s", key)
            return

        async with self._lock:
            zone = self._zones[key]
            actuator_name = command.get("actuator_name", "")
            action = command.get("action", "off")
            value = command.get("value", 0.0) or 0.0
            duration = command.get("duration_seconds")
            act = self._get_actuator(zone, actuator_name)
            if act is None:
                logger.warning("Unknown actuator '%s' for zone %s", actuator_name, key)
                return

            if action in ("on", "set_power"):
                act.active = True
                act.value = value
                act.activated_at = datetime.now(timezone.utc)
                act.duration_seconds = duration
            else:
                act.active = False
                act.value = 0.0
                act.activated_at = None
                act.duration_seconds = None

            logger.info(
                "Applied %s %s to %s (active=%s, duration=%s)",
                actuator_name,
                action,
                key,
                act.active,
                duration,
            )

    async def get_state(self, group_id: str, greenhouse_id: str, zone_id: str) -> ZoneState | None:
        """Return the state for a single zone, or None."""
        return self._zones.get((group_id, greenhouse_id, zone_id))

    async def all_states(self) -> list[ZoneState]:
        """Return all zone states, ticking expired actuators."""
        async with self._lock:
            self._tick_expired()
            return list(self._zones.values())

    async def telemetry_value(self, group_id: str, greenhouse_id: str, zone_id: str, metric: str) -> float:
        """Return the current telemetry value for a metric in a zone,
        factoring in any active actuator effects."""
        zone = self._zones.get((group_id, greenhouse_id, zone_id))
        if zone is None:
            return 0.0

        async with self._lock:
            self._tick_expired()
            base = getattr(zone, metric, 0.0)
            return base + self._actuator_effect(zone, metric)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _base_metrics() -> dict[str, float]:
        return {
            "temperature": 24.0,
            "air_humidity": 60.0,
            "soil_moisture": 55.0,
            "co2": 850.0,
            "light": 500.0,
        }

    @staticmethod
    def _scenario_offsets(scenario: str) -> dict[str, float]:
        return {
            "dry_soil": {"soil_moisture": -40.0},
            "overheating": {"temperature": 16.0},
            "low_light": {"light": -420.0},
            "sensor_fault": {"temperature": 25.0, "air_humidity": -45.0},
        }.get(scenario, {})

    def _tick_expired(self) -> None:
        """Deactivate any actuators whose duration has expired."""
        now = datetime.now(timezone.utc)
        for zone in self._zones.values():
            for act in (zone.pump, zone.fan, zone.heater, zone.lamp):
                if act.active and act.activated_at is not None and act.duration_seconds is not None:
                    elapsed = (now - act.activated_at).total_seconds()
                    if elapsed >= act.duration_seconds:
                        act.active = False
                        act.value = 0.0
                        act.activated_at = None
                        act.duration_seconds = None

    @staticmethod
    def _actuator_effect(zone: ZoneState, metric: str) -> float:
        """Compute the actuator-driven offset for a metric.

        These are intentionally simple linear effects for the
        simulation. They are not meant to model real physics.
        """
        offset = 0.0
        if zone.pump.active and metric == "soil_moisture":
            offset += zone.pump.value * 0.5 if zone.pump.value else 2.0
        if zone.fan.active and metric in ("temperature", "air_humidity"):
            factor = zone.fan.value / 100.0 if zone.fan.value else 0.3
            if metric == "temperature":
                offset -= factor * 2.0
            else:
                offset -= factor * 5.0
        if zone.heater.active and metric == "temperature":
            offset += zone.heater.value * 0.1 if zone.heater.value else 3.0
        if zone.lamp.active and metric == "light":
            offset += zone.lamp.value * 0.5 if zone.lamp.value else 200.0
        return offset

    @staticmethod
    def _get_actuator(zone: ZoneState, name: str) -> ActuatorState | None:
        return {
            "pump": zone.pump,
            "fan": zone.fan,
            "heater": zone.heater,
            "lamp": zone.lamp,
        }.get(name)
