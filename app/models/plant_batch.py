"""Plant batch, profile, control policy, and setpoint models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, IdTimestampMixin


class PlantBatch(Base, IdTimestampMixin):
    """A batch of plants growing in a specific zone."""

    __tablename__ = "plant_batches"

    zone_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("greenhouse_zones.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    species: Mapped[str | None] = mapped_column(String(255))
    cultivar: Mapped[str | None] = mapped_column(String(255))
    planted_at: Mapped[datetime | None] = mapped_column(Date)
    growth_stage: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)

    # -- relationships --
    zone: Mapped["GreenhouseZone"] = relationship(back_populates="plant_batches")  # noqa: F821


class PlantProfile(Base, IdMixin):
    """Describes ideal environmental conditions for a crop/growth stage."""

    __tablename__ = "plant_profiles"

    crop_name: Mapped[str] = mapped_column(String(255), nullable=False)
    growth_stage: Mapped[str | None] = mapped_column(String(50))
    temp_min: Mapped[float | None] = mapped_column(Float)
    temp_opt: Mapped[float | None] = mapped_column(Float)
    temp_max: Mapped[float | None] = mapped_column(Float)
    humidity_min: Mapped[float | None] = mapped_column(Float)
    humidity_opt: Mapped[float | None] = mapped_column(Float)
    humidity_max: Mapped[float | None] = mapped_column(Float)
    soil_moisture_min: Mapped[float | None] = mapped_column(Float)
    soil_moisture_opt: Mapped[float | None] = mapped_column(Float)
    soil_moisture_max: Mapped[float | None] = mapped_column(Float)
    co2_min: Mapped[float | None] = mapped_column(Float)
    co2_opt: Mapped[float | None] = mapped_column(Float)
    co2_max: Mapped[float | None] = mapped_column(Float)
    light_min: Mapped[float | None] = mapped_column(Float)
    light_opt: Mapped[float | None] = mapped_column(Float)
    light_max: Mapped[float | None] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text)


class GroupControlPolicy(Base, IdTimestampMixin):
    """A control policy that can be applied to an entire greenhouse group."""

    __tablename__ = "group_control_policies"

    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("greenhouse_groups.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    policy: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # -- relationships --
    group: Mapped["GreenhouseGroup"] = relationship(back_populates="control_policies")  # noqa: F821


class ControlSetpoint(Base, IdMixin):
    """Current control setpoint target values for a zone."""

    __tablename__ = "control_setpoints"

    zone_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("greenhouse_zones.id"),
        nullable=False,
        unique=True,
    )
    temperature_target: Mapped[float | None] = mapped_column(Float)
    humidity_target: Mapped[float | None] = mapped_column(Float)
    soil_moisture_target: Mapped[float | None] = mapped_column(Float)
    co2_target: Mapped[float | None] = mapped_column(Float)
    light_target: Mapped[float | None] = mapped_column(Float)
    updated_by: Mapped[str | None] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # -- relationships --
    zone: Mapped["GreenhouseZone"] = relationship(back_populates="control_setpoint")  # noqa: F821
