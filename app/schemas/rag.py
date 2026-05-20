"""Pydantic v2 schemas for RAG document ingestion and search."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RAGDocumentCreate(BaseModel):
    """Schema for creating a new RAG document."""

    title: str = Field(..., min_length=1, max_length=255, description="Document title")
    source_type: str | None = Field(
        None,
        max_length=50,
        description="Type of source: manual, url, file, etc.",
    )
    source_url: str | None = Field(None, description="URL of the source document")
    content: str = Field(..., min_length=1, description="Full text content of the document")
    group_id: UUID | None = Field(None, description="Optional group scope")
    metadata_: dict | None = Field(None, alias="metadata", description="Optional metadata")


class RAGDocumentResponse(BaseModel):
    """Schema for returning a RAG document via the API."""

    id: UUID
    group_id: UUID | None
    title: str
    source_type: str | None
    source_url: str | None
    content: str | None
    metadata_: dict | None = Field(None, serialization_alias="metadata")
    created_at: datetime

    model_config = {"from_attributes": True}


class RAGSearchQuery(BaseModel):
    """Schema for semantic search queries."""

    query: str = Field(..., min_length=1, description="Search query text")
    group_id: UUID | None = Field(None, description="Optional group scope")
    limit: int = Field(10, ge=1, le=50, description="Maximum results to return")


class RAGChunkResponse(BaseModel):
    """Schema for returning a search result chunk."""

    content: str
    document_title: str
    score: float
    metadata: dict | None = None
