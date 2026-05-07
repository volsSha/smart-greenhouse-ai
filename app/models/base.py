"""SQLAlchemy 2.0 declarative base and common mixins."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class TimestampMixin:
    """Mixin that adds created_at with server-side default."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class IdMixin:
    """Mixin that adds a UUID primary key with Python-side generation."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )


class IdTimestampMixin(IdMixin, TimestampMixin):
    """Combined mixin for UUID PK + created_at."""

    pass
