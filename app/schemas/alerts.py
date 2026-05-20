"""Pydantic schemas for persisted alerts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class AlertResponse(BaseModel):
    id: UUID
    group_id: UUID
    greenhouse_id: UUID | None
    zone_id: UUID | None
    metric: str | None
    severity: str
    title: str
    message: str
    status: str
    source: str
    created_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class AlertUpdate(BaseModel):
    status: Literal["dismissed"]
