"""Pydantic v2 schemas for command lifecycle and safety validation."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CommandPropose(BaseModel):
    """Schema for proposing a new actuator command."""

    group_id: UUID
    greenhouse_id: UUID
    zone_id: UUID
    actuator: str = Field(..., description="Actuator type, e.g. pump, fan, heater, lamp")
    action: str = Field(..., description="Action: on, off, set_power")
    value: float | None = Field(None, description="Numeric value for set_power actions")
    duration_seconds: int | None = Field(None, ge=0, description="How long to keep the actuator running")
    reason: str | None = Field(None, description="Human-readable reason for the command")
    source: str = Field(
        "manual",
        description="Origin: manual, control_engine, ai_agent, safety_override",
    )


class CommandResponse(BaseModel):
    """Schema for returning a command log entry via the API."""

    id: UUID
    group_id: UUID
    greenhouse_id: UUID
    zone_id: UUID
    actuator_id: UUID | None
    actuator_name: str
    action: str
    value: float | None
    unit: str | None
    duration_seconds: int | None
    source: str
    reason: str | None
    validation_errors: dict | None
    status: str
    valid_until: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CommandApproval(BaseModel):
    """Schema for approving a proposed command."""

    pass
