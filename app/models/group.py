"""Greenhouse group model."""

import uuid

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdTimestampMixin


class GreenhouseGroup(Base, IdTimestampMixin):
    """Represents a group of greenhouses under common management."""

    __tablename__ = "greenhouse_groups"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)

    # -- relationships --
    greenhouses: Mapped[list["Greenhouse"]] = relationship(  # noqa: F821
        back_populates="group",
        cascade="all, delete-orphan",
    )
    control_policies: Mapped[list["GroupControlPolicy"]] = relationship(  # noqa: F821
        back_populates="group",
        cascade="all, delete-orphan",
    )
    command_log: Mapped[list["CommandLog"]] = relationship(  # noqa: F821
        back_populates="group",
        cascade="all, delete-orphan",
    )
    alert_log: Mapped[list["Alert"]] = relationship(  # noqa: F821
        back_populates="group",
        cascade="all, delete-orphan",
    )
    ai_conversations: Mapped[list["AIConversation"]] = relationship(  # noqa: F821
        back_populates="group",
        cascade="all, delete-orphan",
    )
    rag_documents: Mapped[list["RAGDocument"]] = relationship(  # noqa: F821
        back_populates="group",
        cascade="all, delete-orphan",
    )
