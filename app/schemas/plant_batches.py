"""Pydantic v2 schemas for plant batches, profiles, and related entities."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Plant Profile schemas
# ---------------------------------------------------------------------------


class PlantProfileCreate(BaseModel):
    """Schema for creating a new plant profile."""

    crop_name: str = Field(..., max_length=255)
    growth_stage: str | None = Field(None, max_length=50)
    temp_min: float | None = None
    temp_opt: float | None = None
    temp_max: float | None = None
    humidity_min: float | None = None
    humidity_opt: float | None = None
    humidity_max: float | None = None
    soil_moisture_min: float | None = None
    soil_moisture_opt: float | None = None
    soil_moisture_max: float | None = None
    co2_min: float | None = None
    co2_opt: float | None = None
    co2_max: float | None = None
    light_min: float | None = None
    light_opt: float | None = None
    light_max: float | None = None
    description: str | None = None


class PlantProfileUpdate(BaseModel):
    """Schema for updating an existing plant profile. All fields optional."""

    crop_name: str | None = Field(None, max_length=255)
    growth_stage: str | None = Field(None, max_length=50)
    temp_min: float | None = None
    temp_opt: float | None = None
    temp_max: float | None = None
    humidity_min: float | None = None
    humidity_opt: float | None = None
    humidity_max: float | None = None
    soil_moisture_min: float | None = None
    soil_moisture_opt: float | None = None
    soil_moisture_max: float | None = None
    co2_min: float | None = None
    co2_opt: float | None = None
    co2_max: float | None = None
    light_min: float | None = None
    light_opt: float | None = None
    light_max: float | None = None
    description: str | None = None


class PlantProfileResponse(BaseModel):
    """Schema for returning a plant profile."""

    id: UUID
    crop_name: str
    growth_stage: str | None
    temp_min: float | None
    temp_opt: float | None
    temp_max: float | None
    humidity_min: float | None
    humidity_opt: float | None
    humidity_max: float | None
    soil_moisture_min: float | None
    soil_moisture_opt: float | None
    soil_moisture_max: float | None
    co2_min: float | None
    co2_opt: float | None
    co2_max: float | None
    light_min: float | None
    light_opt: float | None
    light_max: float | None
    description: str | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Plant Batch schemas
# ---------------------------------------------------------------------------


class PlantBatchCreate(BaseModel):
    """Schema for creating a new plant batch."""

    zone_id: UUID
    name: str = Field(..., max_length=255)
    species: str | None = Field(None, max_length=255)
    cultivar: str | None = Field(None, max_length=255)
    planted_at: date | None = None
    growth_stage: str | None = Field(None, max_length=50)
    notes: str | None = None


class PlantBatchUpdate(BaseModel):
    """Schema for updating an existing plant batch. All fields optional."""

    name: str | None = Field(None, max_length=255)
    species: str | None = Field(None, max_length=255)
    cultivar: str | None = Field(None, max_length=255)
    planted_at: date | None = None
    growth_stage: str | None = Field(None, max_length=50)
    notes: str | None = None


class PlantBatchResponse(BaseModel):
    """Schema for returning a plant batch."""

    id: UUID
    zone_id: UUID
    name: str
    species: str | None
    cultivar: str | None
    planted_at: date | None
    growth_stage: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Group schemas
# ---------------------------------------------------------------------------


class GroupCreate(BaseModel):
    """Schema for creating a new greenhouse group."""

    name: str = Field(..., max_length=255)
    location: str | None = None
    description: str | None = None


class GroupUpdate(BaseModel):
    """Schema for updating an existing group. All fields optional."""

    name: str | None = Field(None, max_length=255)
    location: str | None = None
    description: str | None = None


class GroupResponse(BaseModel):
    """Schema for returning a greenhouse group."""

    id: UUID
    name: str
    location: str | None
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Greenhouse schemas
# ---------------------------------------------------------------------------


class GreenhouseCreate(BaseModel):
    """Schema for creating a new greenhouse."""

    name: str = Field(..., max_length=255)
    location: str | None = None
    description: str | None = None


class GreenhouseUpdate(BaseModel):
    """Schema for updating a greenhouse. All fields optional."""

    name: str | None = Field(None, max_length=255)
    location: str | None = None
    description: str | None = None


class GreenhouseResponse(BaseModel):
    """Schema for returning a greenhouse."""

    id: UUID
    group_id: UUID
    name: str
    location: str | None
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Zone schemas
# ---------------------------------------------------------------------------


class ZoneCreate(BaseModel):
    """Schema for creating a new zone."""

    name: str = Field(..., max_length=255)
    description: str | None = None


class ZoneUpdate(BaseModel):
    """Schema for updating a zone. All fields optional."""

    name: str | None = Field(None, max_length=255)
    description: str | None = None


class ZoneResponse(BaseModel):
    """Schema for returning a zone."""

    id: UUID
    greenhouse_id: UUID
    name: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Device schemas
# ---------------------------------------------------------------------------


class EdgeNodeCreate(BaseModel):
    """Schema for registering a new edge node."""

    greenhouse_id: UUID
    node_key: str = Field(..., max_length=255)
    name: str = Field(..., max_length=255)
    node_type: str = Field(..., max_length=50)
    firmware_version: str | None = Field(None, max_length=50)


class EdgeNodeResponse(BaseModel):
    """Schema for returning an edge node."""

    id: UUID
    greenhouse_id: UUID
    node_key: str
    name: str
    node_type: str
    firmware_version: str | None
    last_seen_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SensorCreate(BaseModel):
    """Schema for registering a new sensor."""

    zone_id: UUID
    sensor_key: str = Field(..., max_length=255)
    metric: str = Field(..., max_length=100)
    unit: str | None = Field(None, max_length=50)
    edge_node_id: UUID | None = None
    is_active: bool = True


class SensorResponse(BaseModel):
    """Schema for returning a sensor."""

    id: UUID
    zone_id: UUID
    edge_node_id: UUID | None
    sensor_key: str
    metric: str
    unit: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ActuatorCreate(BaseModel):
    """Schema for registering a new actuator."""

    zone_id: UUID
    actuator_key: str = Field(..., max_length=255)
    actuator_type: str = Field(..., max_length=50)
    edge_node_id: UUID | None = None
    is_active: bool = True


class ActuatorResponse(BaseModel):
    """Schema for returning an actuator."""

    id: UUID
    zone_id: UUID
    edge_node_id: UUID | None
    actuator_key: str
    actuator_type: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
