"""Alert log model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdTimestampMixin


class Alert(Base, IdTimestampMixin):
    """Log entry for system-generated alerts."""

    __tablename__ = "alert_log"

    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("greenhouse_groups.id"),
        nullable=False,
    )
    greenhouse_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("greenhouses.id"),
    )
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("greenhouse_zones.id"),
    )
    metric: Mapped[str | None] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(50), nullable=False)  # info | warning | critical
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # active | resolved | dismissed
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # threshold | control_engine | ai_agent | system
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # -- relationships --
    group: Mapped["GreenhouseGroup"] = relationship(back_populates="alert_log")  # noqa: F821
    greenhouse: Mapped["Greenhouse | None"] = relationship(back_populates="alert_log")  # noqa: F821
    zone: Mapped["GreenhouseZone | None"] = relationship(back_populates="alert_log")  # noqa: F821
