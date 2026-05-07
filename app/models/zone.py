"""Greenhouse zone model."""

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdTimestampMixin


class GreenhouseZone(Base, IdTimestampMixin):
    """A zone within a greenhouse (e.g. growing area, nursery)."""

    __tablename__ = "greenhouse_zones"

    greenhouse_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("greenhouses.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # -- relationships --
    greenhouse: Mapped["Greenhouse"] = relationship(back_populates="zones")  # noqa: F821
    sensors: Mapped[list["Sensor"]] = relationship(  # noqa: F821
        back_populates="zone",
        cascade="all, delete-orphan",
    )
    actuators: Mapped[list["Actuator"]] = relationship(  # noqa: F821
        back_populates="zone",
        cascade="all, delete-orphan",
    )
    plant_batches: Mapped[list["PlantBatch"]] = relationship(  # noqa: F821
        back_populates="zone",
        cascade="all, delete-orphan",
    )
    control_setpoint: Mapped["ControlSetpoint | None"] = relationship(  # noqa: F821
        back_populates="zone",
        cascade="all, delete-orphan",
        uselist=False,
    )
    command_log: Mapped[list["CommandLog"]] = relationship(  # noqa: F821
        back_populates="zone",
        cascade="all, delete-orphan",
    )
    alert_log: Mapped[list["Alert"]] = relationship(  # noqa: F821
        back_populates="zone",
        cascade="all, delete-orphan",
    )
    ai_conversations: Mapped[list["AIConversation"]] = relationship(  # noqa: F821
        back_populates="zone",
        cascade="all, delete-orphan",
    )
