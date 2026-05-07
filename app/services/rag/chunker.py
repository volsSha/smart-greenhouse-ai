"""Text chunking for RAG document ingestion.

Splits documents into overlapping chunks, preferring paragraph boundaries
and falling back to sentence-level splitting.
"""

from __future__ import annotations

import re


def chunk_text(
    content: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    """Split text into overlapping chunks.

    Strategy:
    1. Split on paragraph boundaries (double newlines).
    2. Accumulate paragraphs until chunk_size is reached.
    3. If a single paragraph exceeds chunk_size, fall back to sentence splitting.
    4. Overlap is preserved between chunks by re-including the tail of the
       previous chunk at the start of the next chunk.

    Args:
        content: The full document text.
        chunk_size: Target size in characters for each chunk.
        overlap: Number of characters of overlap between consecutive chunks.

    Returns:
        A list of text chunks. Empty strings are filtered out.
    """
    if not content or not content.strip():
        return []

    content = content.strip()

    # Split into paragraphs (separated by one or more blank lines)
    paragraphs = re.split(r"\n\s*\n", content)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return []

    chunks: list[str] = []

    # Build chunks by accumulating paragraphs
    current_parts: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        para_len = len(paragraph)

        # If a single paragraph exceeds chunk_size, split it by sentences
        if para_len > chunk_size:
            # Flush accumulated parts first
            if current_parts:
                chunk_text_joined = " ".join(current_parts)
                chunks.append(chunk_text_joined)
                current_parts = []
                current_length = 0

            # Split the oversized paragraph by sentences
            sentence_chunks = _split_paragraph_by_sentences(
                paragraph, chunk_size, overlap
            )
            chunks.extend(sentence_chunks)
        elif current_length + para_len + (1 if current_parts else 0) > chunk_size:
            # Current chunk is full, flush it
            chunk_text_joined = " ".join(current_parts)
            chunks.append(chunk_text_joined)

            # Start new chunk with overlap from the tail
            overlap_text = _extract_overlap_tail(chunk_text_joined, overlap)
            current_parts = [overlap_text, paragraph] if overlap_text else [paragraph]
            current_length = sum(len(p) for p in current_parts) + max(0, len(current_parts) - 1)
        else:
            current_parts.append(paragraph)
            current_length += para_len + (1 if len(current_parts) > 1 else 0)

    # Flush remaining
    if current_parts:
        chunk_text_joined = " ".join(current_parts)
        chunks.append(chunk_text_joined)

    # Filter empty chunks
    return [c.strip() for c in chunks if c.strip()]


def _split_paragraph_by_sentences(
    paragraph: str,
    chunk_size: int,
    overlap: int,
) -> list[str]:
    """Split a single paragraph into sentence-based chunks with overlap."""
    # Split on sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return []

    chunks: list[str] = []
    current_parts: list[str] = []
    current_length = 0

    for sentence in sentences:
        sent_len = len(sentence)

        if current_length + sent_len + (1 if current_parts else 0) > chunk_size and current_parts:
            chunk_text_joined = " ".join(current_parts)
            chunks.append(chunk_text_joined)

            # Overlap from tail
            overlap_text = _extract_overlap_tail(chunk_text_joined, overlap)
            current_parts = [overlap_text, sentence] if overlap_text else [sentence]
            current_length = sum(len(p) for p in current_parts) + max(0, len(current_parts) - 1)
        else:
            current_parts.append(sentence)
            current_length += sent_len + (1 if len(current_parts) > 1 else 0)

    if current_parts:
        chunks.append(" ".join(current_parts))

    return [c.strip() for c in chunks if c.strip()]


def _extract_overlap_tail(text: str, overlap_size: int) -> str:
    """Extract the tail of a text string for overlap, breaking at a word boundary."""
    if overlap_size <= 0 or len(text) <= overlap_size:
        return ""

    tail = text[-overlap_size:]

    # Try to break at a word boundary to avoid cutting words
    space_idx = tail.find(" ")
    if space_idx > 0:
        tail = tail[space_idx + 1 :]

    return tail.strip()
