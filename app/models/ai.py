"""AI conversation, message, and tool call models."""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdTimestampMixin


class AIConversation(Base, IdTimestampMixin):
    """A conversation session between a user and the AI agent."""

    __tablename__ = "ai_conversations"

    group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("greenhouse_groups.id"),
    )
    greenhouse_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("greenhouses.id"),
    )
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("greenhouse_zones.id"),
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column()
    title: Mapped[str | None] = mapped_column(String(255))

    # -- relationships --
    group: Mapped["GreenhouseGroup | None"] = relationship(back_populates="ai_conversations")  # noqa: F821
    greenhouse: Mapped["Greenhouse | None"] = relationship(back_populates="ai_conversations")  # noqa: F821
    zone: Mapped["GreenhouseZone | None"] = relationship(back_populates="ai_conversations")  # noqa: F821
    messages: Mapped[list["AIMessage"]] = relationship(  # noqa: F821
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AIMessage.created_at",
    )
    tool_calls: Mapped[list["AIToolCall"]] = relationship(  # noqa: F821
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class AIMessage(Base, IdTimestampMixin):
    """A single message within an AI conversation."""

    __tablename__ = "ai_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_conversations.id"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(String(100))
    token_input: Mapped[int | None] = mapped_column(Integer)
    token_output: Mapped[int | None] = mapped_column(Integer)

    # -- relationships --
    conversation: Mapped["AIConversation"] = relationship(back_populates="messages")  # noqa: F821


class AIToolCall(Base, IdTimestampMixin):
    """Record of a tool invocation during an AI conversation."""

    __tablename__ = "ai_tool_calls"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_conversations.id"),
        nullable=False,
    )
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    arguments: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    error: Mapped[str | None] = mapped_column(Text)

    # -- relationships --
    conversation: Mapped["AIConversation"] = relationship(back_populates="tool_calls")  # noqa: F821
