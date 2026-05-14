"""Threshold evaluation service.

Compares current sensor readings against plant profile thresholds for a
zone and generates alerts when values fall outside acceptable ranges.

Severity logic:
  - **warning**: value is slightly outside min/max (within 20% margin)
  - **critical**: value is far outside min/max (beyond 20% margin)
"""

from __future__ import annotations

import uuid
import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.plant_batch import PlantProfile
from app.repositories.plant_batch_repository import PlantBatchRepository, PlantProfileRepository
from app.repositories.zone_repository import ZoneRepository
from app.repositories.greenhouse_repository import GreenhouseRepository
from app.repositories.alert_repository import AlertRepository

logger = logging.getLogger(__name__)

# Mapping from telemetry metric names to PlantProfile threshold attribute pairs.
# Each entry is (min_attr, max_attr).
METRIC_THRESHOLD_MAP: dict[str, tuple[str, str]] = {
    "temperature": ("temp_min", "temp_max"),
    "air_humidity": ("humidity_min", "humidity_max"),
    "soil_moisture": ("soil_moisture_min", "soil_moisture_max"),
    "co2": ("co2_min", "co2_max"),
    "light": ("light_min", "light_max"),
}

# Percentage margin beyond min/max before upgrading from warning to critical.
CRITICAL_MARGIN_PCT = 0.20


@dataclass(frozen=True)
class ThresholdResult:
    """Result of evaluating a single metric against its threshold."""

    metric: str
    value: float
    threshold_min: float | None
    threshold_max: float | None
    severity: str | None  # "warning" or "critical", or None if in range
    message: str


class ThresholdService:
    """Evaluates sensor readings against plant profile thresholds."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _compute_severity(
        self,
        value: float,
        min_val: float,
        max_val: float,
    ) -> tuple[str, str]:
        """Determine alert severity and message for a value outside range.

        Returns (severity, message).
        """
        range_width = max_val - min_val
        margin = range_width * CRITICAL_MARGIN_PCT

        if value < min_val:
            deficit = min_val - value
            if deficit > margin:
                severity = "critical"
                msg = (
                    f"{value} is critically low (threshold min {min_val}, "
                    f"max {max_val})"
                )
            else:
                severity = "warning"
                msg = f"{value} is below minimum threshold (min {min_val})"
            return severity, msg
        else:
            excess = value - max_val
            if excess > margin:
                severity = "critical"
                msg = (
                    f"{value} is critically high (threshold min {min_val}, "
                    f"max {max_val})"
                )
            else:
                severity = "warning"
                msg = f"{value} is above maximum threshold (max {max_val})"
            return severity, msg

    def evaluate_readings(
        self,
        profile: PlantProfile,
        current_readings: dict[str, float],
    ) -> list[ThresholdResult]:
        """Compare current readings against profile thresholds.

        Returns a list of ThresholdResult for every metric that is
        out of range. Metrics with no matching threshold definition or
        where min/max are None on the profile are skipped.
        """
        results: list[ThresholdResult] = []

        for metric, value in current_readings.items():
            if metric not in METRIC_THRESHOLD_MAP:
                continue

            min_attr, max_attr = METRIC_THRESHOLD_MAP[metric]
            min_val = getattr(profile, min_attr, None)
            max_val = getattr(profile, max_attr, None)

            if min_val is None or max_val is None:
                # No thresholds defined for this metric in the profile.
                continue

            if min_val <= value <= max_val:
                # Within acceptable range -- no alert needed.
                continue

            severity, message = self._compute_severity(value, min_val, max_val)
            results.append(
                ThresholdResult(
                    metric=metric,
                    value=value,
                    threshold_min=min_val,
                    threshold_max=max_val,
                    severity=severity,
                    message=message,
                )
            )

        return results

    async def evaluate_zone(
        self,
        zone_id: uuid.UUID,
        current_readings: dict[str, float],
    ) -> list[Alert]:
        """Evaluate current readings for a zone and create alerts.

        Looks up plant batches in the zone, finds the matching plant
        profile based on species and growth_stage, evaluates all readings
        against the profile thresholds, and creates Alert records for
        any out-of-range values.

        Returns a list of newly created Alert objects.
        """
        zone_repo = ZoneRepository(self.session)
        batch_repo = PlantBatchRepository(self.session)
        profile_repo = PlantProfileRepository(self.session)
        alert_repo = AlertRepository(self.session)

        zone = await zone_repo.get_by_id(zone_id)
        if zone is None:
            logger.warning("Threshold evaluation: zone %s not found", zone_id)
            return []

        # Find plant batches for this zone
        batches = await batch_repo.list_by_zone(zone_id)
        if not batches:
            logger.debug(
                "Threshold evaluation: no plant batches in zone %s", zone_id
            )
            return []

        # Use the first batch to find a matching profile
        batch = batches[0]
        profile: PlantProfile | None = None

        if batch.species:
            profile = await profile_repo.find_by_crop_and_stage(
                crop_name=batch.species,
                growth_stage=batch.growth_stage,
            )

        if profile is None:
            logger.debug(
                "Threshold evaluation: no matching profile for species=%s "
                "stage=%s in zone %s",
                batch.species,
                batch.growth_stage,
                zone_id,
            )
            return []

        # Evaluate readings against profile
        results = self.evaluate_readings(profile, current_readings)

        # Resolve group_id for alerts
        group_id = zone.greenhouse_id  # type: ignore[assignment]
        # We need the group_id, not greenhouse_id. Look up the greenhouse.
        gh_repo = GreenhouseRepository(self.session)
        greenhouse = await gh_repo.get_by_id(zone.greenhouse_id)
        if greenhouse is None:
            logger.warning(
                "Threshold evaluation: greenhouse %s not found for zone %s",
                zone.greenhouse_id,
                zone_id,
            )
            return []

        group_id = greenhouse.group_id

        alerts: list[Alert] = []
        for result in results:
            if result.severity is None:
                continue

            alert = await alert_repo.create(
                group_id=group_id,
                greenhouse_id=greenhouse.id,
                zone_id=zone_id,
                metric=result.metric,
                severity=result.severity,
                title=f"{result.metric} {result.severity} in zone {zone.name}",
                message=result.message,
                status="active",
                source="threshold",
            )
            alerts.append(alert)

        logger.info(
            "Threshold evaluation for zone %s: %d alert(s) generated",
            zone_id,
            len(alerts),
        )
        return alerts
