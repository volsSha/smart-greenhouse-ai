"""RAG document and chunk models."""

import uuid
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdTimestampMixin


class RAGDocument(Base, IdTimestampMixin):
    """A source document ingested for RAG retrieval."""

    __tablename__ = "rag_documents"

    group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("greenhouse_groups.id"),
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(50))
    source_url: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    # -- relationships --
    group: Mapped["GreenhouseGroup | None"] = relationship(back_populates="rag_documents")  # noqa: F821
    chunks: Mapped[list["RAGChunk"]] = relationship(  # noqa: F821
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="RAGChunk.chunk_index",
    )


class RAGChunk(Base, IdTimestampMixin):
    """A chunk of a RAG document with its embedding vector."""

    __tablename__ = "rag_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rag_documents.id"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Any | None] = mapped_column(Vector(1536))
    embedding_model: Mapped[str | None] = mapped_column(String(100))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    # -- relationships --
    document: Mapped["RAGDocument"] = relationship(back_populates="chunks")  # noqa: F821
