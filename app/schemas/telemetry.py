"""Strict Pydantic v2 schemas for MQTT telemetry messages.

Telemetry messages arrive via MQTT on topics of the form::

    greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/telemetry

The payload is a JSON ``TelemetryEnvelope`` wrapping a ``TelemetryReading``.
Validation rejects unknown metrics, non-numeric values, and timestamps
outside the configurable acceptance window.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.core.safety_limits import VALID_METRICS

logger = logging.getLogger(__name__)

# Timestamp acceptance window: readings more than this far from "now" are
# rejected.  This prevents replay attacks and clock-skew garbage.
DEFAULT_ACCEPTANCE_WINDOW = timedelta(minutes=5)


class Quality(str, Enum):
    """Sensor reading quality indicator."""

    OK = "ok"
    WARN = "warn"
    ERROR = "error"


class TelemetryReading(BaseModel):
    """A single sensor reading from a greenhouse zone.

    Attributes:
        group_id: Fleet group identifier (e.g. ``"group-001-vegetable-production"``).
        greenhouse_id: Greenhouse within the group (e.g. ``"gh-001-tomatoes"``).
        zone_id: Zone within the greenhouse (e.g. ``"zone-01-seedlings"``).
        sensor_id: Logical sensor identifier (e.g. ``"temp-01"``).
        metric: The measured quantity — must be one of ``VALID_METRICS``.
        value: Numeric sensor value.
        quality: Reading quality — ``"ok"``, ``"warn"``, or ``"error"``.
        timestamp: UTC timestamp of when the reading was taken.
    """

    group_id: str
    greenhouse_id: str
    zone_id: str
    sensor_id: str
    metric: str
    value: float
    quality: Quality = Quality.OK
    timestamp: datetime

    # ---------- validators ----------

    @field_validator("metric")
    @classmethod
    def metric_must_be_known(cls, v: str) -> str:
        if v not in VALID_METRICS:
            raise ValueError(
                f"Unknown metric '{v}'. Valid metrics: {sorted(VALID_METRICS)}"
            )
        return v

    @field_validator("value")
    @classmethod
    def value_must_be_numeric_compatible(cls, v: float) -> float:
        # Pydantic already coerces to float, but we guard against NaN / Inf
        # which would silently corrupt downstream analytics.
        import math

        if math.isnan(v) or math.isinf(v):
            raise ValueError("Sensor value must be a finite number")
        return v


class TelemetryEnvelope(BaseModel):
    """Wrapper around :class:`TelemetryReading` carrying MQTT metadata.

    ``message_id`` is optional but, when present, enables idempotent
    deduplication inside the ingestion pipeline.
    """

    message_id: str | None = None
    qos: int = Field(default=0, ge=0, le=2)
    reading: TelemetryReading

    @field_validator("qos")
    @classmethod
    def qos_in_range(cls, v: int) -> int:
        if v not in (0, 1, 2):
            raise ValueError("QoS must be 0, 1, or 2")
        return v


class TelemetryValidator:
    """Stateful validator that enforces a timestamp acceptance window.

    Tests can inject a deterministic reference point.
    """

    def __init__(
        self,
        now: datetime | None = None,
        window: timedelta = DEFAULT_ACCEPTANCE_WINDOW,
    ) -> None:
        self._now = now
        self._window = window

    def validate_timestamp(self, ts: datetime) -> None:
        """Raise ``ValueError`` if *ts* is outside the acceptance window."""
        now = self._now or datetime.now(timezone.utc)
        delta = ts - now
        if abs(delta) > self._window:
            raise ValueError(
                f"Timestamp {ts.isoformat()} is outside the acceptance window "
                f"(+/- {self._window}). Reference now: {now.isoformat()}"
            )
