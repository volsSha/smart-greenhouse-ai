"""Greenhouse model."""

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdTimestampMixin


class Greenhouse(Base, IdTimestampMixin):
    """A single greenhouse within a group."""

    __tablename__ = "greenhouses"

    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("greenhouse_groups.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)

    # -- relationships --
    group: Mapped["GreenhouseGroup"] = relationship(back_populates="greenhouses")  # noqa: F821
    zones: Mapped[list["GreenhouseZone"]] = relationship(  # noqa: F821
        back_populates="greenhouse",
        cascade="all, delete-orphan",
    )
    edge_nodes: Mapped[list["EdgeNode"]] = relationship(  # noqa: F821
        back_populates="greenhouse",
        cascade="all, delete-orphan",
    )
    command_log: Mapped[list["CommandLog"]] = relationship(  # noqa: F821
        back_populates="greenhouse",
        cascade="all, delete-orphan",
    )
    alert_log: Mapped[list["Alert"]] = relationship(  # noqa: F821
        back_populates="greenhouse",
        cascade="all, delete-orphan",
    )
    ai_conversations: Mapped[list["AIConversation"]] = relationship(  # noqa: F821
        back_populates="greenhouse",
        cascade="all, delete-orphan",
    )
