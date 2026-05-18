"""Edge node, sensor, and actuator registry models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdTimestampMixin


class EdgeNode(Base, IdTimestampMixin):
    """An edge device (ESP32, simulator, gateway) attached to a greenhouse."""

    __tablename__ = "edge_nodes"

    greenhouse_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("greenhouses.id"),
        nullable=False,
    )
    node_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)  # esp32 | simulator | gateway
    firmware_version: Mapped[str | None] = mapped_column(String(50))
    mqtt_username: Mapped[str | None] = mapped_column(String(255))
    mqtt_token: Mapped[str | None] = mapped_column(String(255))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # -- relationships --
    greenhouse: Mapped["Greenhouse"] = relationship(back_populates="edge_nodes")  # noqa: F821
    sensors: Mapped[list["Sensor"]] = relationship(  # noqa: F821
        back_populates="edge_node",
        cascade="all, delete-orphan",
    )
    actuators: Mapped[list["Actuator"]] = relationship(  # noqa: F821
        back_populates="edge_node",
        cascade="all, delete-orphan",
    )


class Sensor(Base, IdTimestampMixin):
    """A registered sensor within a zone, optionally bound to an edge node."""

    __tablename__ = "sensor_registry"
    __table_args__ = (
        UniqueConstraint("zone_id", "sensor_key", name="uq_sensor_zone_key"),
    )

    zone_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("greenhouse_zones.id"),
        nullable=False,
    )
    edge_node_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("edge_nodes.id"),
    )
    sensor_key: Mapped[str] = mapped_column(String(255), nullable=False)
    metric: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # -- relationships --
    zone: Mapped["GreenhouseZone"] = relationship(back_populates="sensors")  # noqa: F821
    edge_node: Mapped["EdgeNode | None"] = relationship(back_populates="sensors")


class Actuator(Base, IdTimestampMixin):
    """A registered actuator within a zone, optionally bound to an edge node."""

    __tablename__ = "actuator_registry"
    __table_args__ = (
        UniqueConstraint("zone_id", "actuator_key", name="uq_actuator_zone_key"),
    )

    zone_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("greenhouse_zones.id"),
        nullable=False,
    )
    edge_node_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("edge_nodes.id"),
    )
    actuator_key: Mapped[str] = mapped_column(String(255), nullable=False)
    actuator_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pump | fan | heater | lamp
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # -- relationships --
    zone: Mapped["GreenhouseZone"] = relationship(back_populates="actuators")  # noqa: F821
    edge_node: Mapped["EdgeNode | None"] = relationship(back_populates="actuators")
    command_log: Mapped[list["CommandLog"]] = relationship(  # noqa: F821
        back_populates="actuator_ref",
        foreign_keys="CommandLog.actuator_id",
        passive_deletes=True,
    )
