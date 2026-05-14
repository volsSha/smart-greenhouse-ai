"""Simulation scenario generators for multi-greenhouse telemetry.

Each scenario produces realistic sensor readings within configured bounds,
with random noise for natural variation. Scenarios are used by the simulator
entry point to publish MQTT telemetry.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.safety_limits import VALID_METRICS


@dataclass
class SensorBounds:
    """Min/max bounds for a single metric."""

    min_val: float
    max_val: float
    unit: str = ""


# Default realistic ranges for each metric.
DEFAULT_BOUNDS: dict[str, SensorBounds] = {
    "temperature": SensorBounds(15.0, 35.0, "°C"),
    "air_humidity": SensorBounds(30.0, 90.0, "%"),
    "co2": SensorBounds(300.0, 1500.0, "ppm"),
    "light": SensorBounds(0.0, 80000.0, "lux"),
    "soil_moisture": SensorBounds(20.0, 80.0, "%"),
    "fan_power": SensorBounds(0.0, 100.0, "%"),
    "pump_state": SensorBounds(0.0, 1.0, ""),
    "heater_power": SensorBounds(0.0, 100.0, "%"),
    "lamp_state": SensorBounds(0.0, 1.0, ""),
}


@dataclass
class ScenarioReading:
    """A generated telemetry reading ready for MQTT publishing."""

    sensor_id: str
    metric: str
    value: float
    quality: str = "ok"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class Scenario(ABC):
    """Base class for simulation scenarios."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    def generate_reading(self, metric: str, sensor_id: str) -> ScenarioReading: ...

    def generate_all_metrics(
        self, sensor_prefix: str, metrics: list[str] | None = None
    ) -> list[ScenarioReading]:
        """Generate readings for all metrics (or a subset)."""
        metrics = metrics or VALID_METRICS
        return [
            self.generate_reading(metric, f"{sensor_prefix}-{metric[:5]}")
            for metric in metrics
        ]


class NormalScenario(Scenario):
    """Normal operating conditions within expected ranges."""

    @property
    def name(self) -> str:
        return "normal"

    @property
    def description(self) -> str:
        return "Normal greenhouse conditions with realistic sensor variation"

    def generate_reading(self, metric: str, sensor_id: str) -> ScenarioReading:
        bounds = DEFAULT_BOUNDS[metric]
        midpoint = (bounds.min_val + bounds.max_val) / 2
        noise = random.uniform(-0.1, 0.1) * (bounds.max_val - bounds.min_val)
        value = round(midpoint + noise, 2)
        value = max(bounds.min_val, min(bounds.max_val, value))
        return ScenarioReading(
            sensor_id=sensor_id,
            metric=metric,
            value=value,
            quality="ok",
        )


class DrySoilScenario(Scenario):
    """Simulates low soil moisture conditions (20-30%)."""

    @property
    def name(self) -> str:
        return "dry_soil"

    @property
    def description(self) -> str:
        return "Low soil moisture readings simulating drought stress"

    def generate_reading(self, metric: str, sensor_id: str) -> ScenarioReading:
        if metric == "soil_moisture":
            value = round(random.uniform(20.0, 30.0), 2)
            quality = "warn" if value < 25.0 else "ok"
            return ScenarioReading(sensor_id=sensor_id, metric=metric, value=value, quality=quality)

        # Other metrics remain normal.
        return NormalScenario().generate_reading(metric, sensor_id)


class OverheatingScenario(Scenario):
    """Simulates high temperature conditions (35-45°C)."""

    @property
    def name(self) -> str:
        return "overheating"

    @property
    def description(self) -> str:
        return "High temperature readings simulating heat stress"

    def generate_reading(self, metric: str, sensor_id: str) -> ScenarioReading:
        if metric == "temperature":
            value = round(random.uniform(35.0, 45.0), 2)
            quality = "critical" if value > 40.0 else "warn"
            return ScenarioReading(sensor_id=sensor_id, metric=metric, value=value, quality=quality)

        return NormalScenario().generate_reading(metric, sensor_id)


class LowLightScenario(Scenario):
    """Simulates low light conditions (50-200 lux)."""

    @property
    def name(self) -> str:
        return "low_light"

    @property
    def description(self) -> str:
        return "Low light intensity simulating poor lighting conditions"

    def generate_reading(self, metric: str, sensor_id: str) -> ScenarioReading:
        if metric == "light":
            value = round(random.uniform(50.0, 200.0), 2)
            return ScenarioReading(sensor_id=sensor_id, metric=metric, value=value, quality="warn")

        return NormalScenario().generate_reading(metric, sensor_id)


class SensorFaultScenario(Scenario):
    """Simulates sensor malfunction with error quality readings."""

    @property
    def name(self) -> str:
        return "sensor_fault"

    @property
    def description(self) -> str:
        return "Sensor malfunction producing error quality readings"

    def generate_reading(self, metric: str, sensor_id: str) -> ScenarioReading:
        return ScenarioReading(
            sensor_id=sensor_id,
            metric=metric,
            value=round(random.uniform(-999.0, 0.0), 2),
            quality="error",
        )


ALL_SCENARIOS: list[type[Scenario]] = [
    NormalScenario,
    DrySoilScenario,
    OverheatingScenario,
    LowLightScenario,
    SensorFaultScenario,
]
