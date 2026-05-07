"""Command log model for tracking actuator commands."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdTimestampMixin


class CommandLog(Base, IdTimestampMixin):
    """Log of every actuator command sent through the system."""

    __tablename__ = "command_log"

    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("greenhouse_groups.id"),
        nullable=False,
    )
    greenhouse_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("greenhouses.id"),
        nullable=False,
    )
    zone_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("greenhouse_zones.id"),
        nullable=False,
    )
    actuator_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("actuator_registry.id"),
    )
    actuator_name: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(50))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # manual | control_engine | ai_agent | safety_override
    reason: Mapped[str | None] = mapped_column(Text)
    validation_errors: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # proposed | validated | approved | executing | executed | cancelled | rejected | expired | failed
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # -- relationships --
    group: Mapped["GreenhouseGroup"] = relationship(back_populates="command_log")  # noqa: F821
    greenhouse: Mapped["Greenhouse"] = relationship(back_populates="command_log")  # noqa: F821
    zone: Mapped["GreenhouseZone"] = relationship(back_populates="command_log")  # noqa: F821
    actuator_ref: Mapped["Actuator | None"] = relationship(  # noqa: F821
        back_populates="command_log",
        foreign_keys=[actuator_id],
    )
