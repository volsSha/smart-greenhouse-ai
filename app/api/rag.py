"""REST endpoints for RAG document ingestion, reindex, and search."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.schemas.rag import (
    RAGChunkResponse,
    RAGDocumentCreate,
    RAGDocumentResponse,
)
from app.services.rag.embedding_client import EmbeddingClient, EmbeddingError
from app.services.rag.reindex_service import ReindexService
from app.services.rag.templates import RAGTemplateDocument, load_ukrainian_greenhouse_templates
from app.repositories.rag_repository import RAGRepository
from app.services.rag.chunker import chunk_text
from app.config import get_settings

router = APIRouter(prefix="/api/rag", tags=["rag"])


def _build_embedding_client() -> EmbeddingClient:
    """Build an EmbeddingClient from application settings."""
    settings = get_settings()
    return EmbeddingClient(
        api_key=settings.openrouter.api_key,
        base_url=settings.openrouter.base_url,
        model=settings.openrouter.embedding_model,
        dimension=settings.openrouter.embedding_dimension,
    )


async def _create_indexed_document(
    repo: RAGRepository,
    body: RAGDocumentCreate,
    embedding_client: EmbeddingClient | None = None,
):
    document = await repo.create_document(
        title=body.title,
        content=body.content,
        source_type=body.source_type,
        source_url=body.source_url,
        group_id=body.group_id,
        metadata_=body.metadata_,
    )

    chunks = chunk_text(body.content)
    if chunks:
        client = embedding_client or _build_embedding_client()
        try:
            embeddings = await client.embed(chunks)
        except EmbeddingError as e:
            raise HTTPException(status_code=502, detail=str(e))

        await repo.add_chunks(
            document.id,
            [
                {
                    "chunk_index": i,
                    "content": chunk,
                    "embedding": embedding,
                    "embedding_model": client.model_name,
                    "metadata": None,
                }
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
            ],
        )

    return document


@router.post("/documents", response_model=RAGDocumentResponse, status_code=201)
async def create_document(
    body: RAGDocumentCreate,
    session: AsyncSession = Depends(get_db_session),
) -> RAGDocumentResponse:
    """Add a document to the RAG knowledge base.

    The document is chunked and embedded immediately.
    """
    repo = RAGRepository(session)
    document = await _create_indexed_document(repo, body)
    await session.commit()
    await session.refresh(document)
    return RAGDocumentResponse.model_validate(document)


def _template_to_create_body(template: RAGTemplateDocument) -> RAGDocumentCreate:
    return RAGDocumentCreate(
        title=template.title,
        source_type="template",
        source_url=template.source_url,
        content=template.content,
        metadata=template.metadata,
    )


@router.post("/documents/templates/ukrainian-greenhouse", status_code=201)
async def create_ukrainian_greenhouse_templates(
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Seed built-in Ukrainian greenhouse research documents."""
    repo = RAGRepository(session)
    embedding_client = _build_embedding_client()
    documents = []

    for template in load_ukrainian_greenhouse_templates():
        document = await _create_indexed_document(
            repo,
            _template_to_create_body(template),
            embedding_client,
        )
        documents.append(document)

    await session.commit()
    return {"created": len(documents), "documents": [RAGDocumentResponse.model_validate(document) for document in documents]}


@router.get("/documents", response_model=list[RAGDocumentResponse])
async def list_documents(
    group_id: UUID | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[RAGDocumentResponse]:
    """List all RAG documents, optionally filtered by group."""
    repo = RAGRepository(session)
    documents = await repo.list_documents(group_id=group_id)
    return [RAGDocumentResponse.model_validate(d) for d in documents]


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a RAG document and its chunks."""
    repo = RAGRepository(session)
    deleted = await repo.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    await session.commit()


@router.post("/reindex")
async def reindex_documents(
    document_id: UUID | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Trigger reindexing of RAG documents.

    If document_id is provided, reindex only that document.
    Otherwise, reindex all documents.
    """
    embedding_client = _build_embedding_client()
    repo = RAGRepository(session)
    service = ReindexService(repo, embedding_client)

    if document_id is not None:
        try:
            result = await service.reindex_document(document_id)
            await session.commit()
            return {"results": [result]}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    else:
        results = await service.reindex_all()
        await session.commit()
        return {"results": results}


@router.get("/search", response_model=list[RAGChunkResponse])
async def search_knowledge(
    query: str,
    group_id: UUID | None = None,
    limit: int = 10,
    session: AsyncSession = Depends(get_db_session),
) -> list[RAGChunkResponse]:
    """Semantic search over the RAG knowledge base."""
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty")

    # Generate embedding for the query
    try:
        embedding_client = _build_embedding_client()
        embeddings = await embedding_client.embed([query])
    except EmbeddingError as e:
        raise HTTPException(status_code=502, detail=str(e))

    query_embedding = embeddings[0]

    repo = RAGRepository(session)
    results = await repo.search(
        query_embedding=query_embedding,
        limit=limit,
        group_id=group_id,
    )

    return [
        RAGChunkResponse(
            content=r["content"],
            document_title=r["document_title"],
            score=r["score"],
            metadata=r["metadata"],
        )
        for r in results
    ]
