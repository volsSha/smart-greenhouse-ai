"""API-facing telemetry schemas for HTTP request/response models.

These schemas expose telemetry data via the REST API, separate from the
internal MQTT envelope schemas in :mod:`app.schemas.telemetry`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TelemetryReadingResponse(BaseModel):
    """A single telemetry reading returned by the REST API."""

    group_id: str
    greenhouse_id: str
    zone_id: str
    sensor_id: str
    metric: str
    value: float
    quality: str = "ok"
    timestamp: datetime


class TelemetryBatchResponse(BaseModel):
    """Paginated batch of telemetry readings."""

    readings: list[TelemetryReadingResponse]
    total: int = 0
    offset: int = 0
    limit: int = Field(default=100, le=1000)


class TelemetryQueryParams(BaseModel):
    """Query parameters for filtering telemetry readings."""

    group_id: str | None = None
    greenhouse_id: str | None = None
    zone_id: str | None = None
    metric: str | None = None
    quality: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
