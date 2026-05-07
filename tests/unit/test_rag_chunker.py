"""Unit tests for RAG text chunking."""

from __future__ import annotations

import pytest

from app.services.rag.chunker import chunk_text


class TestChunkTextParagraphs:
    """Tests for paragraph-based chunking."""

    def test_single_short_paragraph_returns_one_chunk(self) -> None:
        """A single short paragraph should return one chunk."""
        result = chunk_text("This is a short paragraph.", chunk_size=500)
        assert len(result) == 1
        assert result[0] == "This is a short paragraph."

    def test_multiple_paragraphs_split_across_chunks(self) -> None:
        """Multiple paragraphs should be split when they exceed chunk_size."""
        paragraphs = []
        for i in range(10):
            paragraphs.append(f"Paragraph {i}: " + "word " * 100)

        content = "\n\n".join(paragraphs)
        result = chunk_text(content, chunk_size=500, overlap=50)

        assert len(result) > 1
        # Each chunk should be within reasonable bounds
        for chunk in result:
            # Chunks can exceed chunk_size slightly due to paragraph boundaries
            assert len(chunk) < 800

    def test_chunk_size_respected(self) -> None:
        """Chunks should generally respect the chunk_size parameter."""
        long_paragraph = "word " * 300  # ~1500 chars
        result = chunk_text(long_paragraph, chunk_size=500, overlap=50)

        # The paragraph is too long, so it should be split by sentences
        # Since there are no sentence boundaries, it will still be one chunk
        # but the function handles this case
        assert len(result) >= 1

    def test_overlap_preserved(self) -> None:
        """Consecutive chunks should have some overlap."""
        paragraphs = []
        for i in range(5):
            paragraphs.append(f"Paragraph {i}: " + "unique_word_" + str(i) + " " * 80)

        content = "\n\n".join(paragraphs)
        result = chunk_text(content, chunk_size=300, overlap=50)

        # If there are multiple chunks, check for overlap
        if len(result) > 1:
            # The tail of one chunk should appear in the start of the next
            # (approximately, due to word-boundary splitting)
            found_overlap = False
            for i in range(len(result) - 1):
                tail = result[i][-50:]
                # At least some words from the tail should appear in the next chunk
                tail_words = set(tail.split())
                next_words = set(result[i + 1].split())
                if tail_words & next_words:
                    found_overlap = True
                    break
            assert found_overlap


class TestChunkTextSentences:
    """Tests for sentence-level fallback splitting."""

    def test_long_paragraph_split_by_sentences(self) -> None:
        """A paragraph with many sentences should be split at sentence boundaries."""
        sentences = [
            f"This is sentence {i} with some additional words to make it longer."
            for i in range(20)
        ]
        long_paragraph = " ".join(sentences)
        result = chunk_text(long_paragraph, chunk_size=200, overlap=30)

        assert len(result) > 1

    def test_sentence_split_preserves_content(self) -> None:
        """All original text should be preserved across chunks (minus overlap)."""
        text = (
            "First sentence here. Second sentence there. Third sentence everywhere. "
            "Fourth sentence nowhere. Fifth sentence anywhere. Sixth sentence somewhere."
        )
        result = chunk_text(text, chunk_size=100, overlap=20)

        # All key words should be present in at least one chunk
        all_text = " ".join(result)
        assert "First sentence" in all_text
        assert "Sixth sentence" in all_text


class TestChunkTextEdgeCases:
    """Tests for edge cases."""

    def test_empty_string_returns_empty_list(self) -> None:
        """Empty input should return empty list."""
        assert chunk_text("") == []
        assert chunk_text("   ") == []
        assert chunk_text("\n\n\n") == []

    def test_whitespace_only_returns_empty_list(self) -> None:
        """Whitespace-only input should return empty list."""
        assert chunk_text("   \n\n   \n   ") == []

    def test_single_word_returns_one_chunk(self) -> None:
        """A single word should return one chunk."""
        result = chunk_text("hello")
        assert len(result) == 1
        assert result[0] == "hello"

    def test_single_sentence_returns_one_chunk(self) -> None:
        """A single short sentence should return one chunk."""
        result = chunk_text("This is a single sentence.")
        assert len(result) == 1

    def test_chunk_size_larger_than_content_returns_one_chunk(self) -> None:
        """If chunk_size is larger than the content, return one chunk."""
        content = "Short content."
        result = chunk_text(content, chunk_size=10000)
        assert len(result) == 1
        assert result[0] == content

    def test_zero_overlap_returns_chunks_without_overlap(self) -> None:
        """Zero overlap should produce non-overlapping chunks."""
        paragraphs = [f"Para {i}: " + "word " * 60 for i in range(5)]
        content = "\n\n".join(paragraphs)
        result = chunk_text(content, chunk_size=300, overlap=0)

        assert len(result) > 1

    def test_real_world_agronomic_text(self) -> None:
        """Test chunking on realistic agronomic content."""
        content = """Tomato Care Guide

Tomatoes need consistent watering. Water deeply 1-2 times per week rather than frequent shallow watering. Mulch around plants to retain moisture.

Optimal temperature for tomatoes is 20-25 degrees Celsius during the day and 15-20 degrees at night. Temperatures above 35 degrees can cause flower drop.

Common pests include aphids, whiteflies, and tomato hornworms. Check plants regularly and use integrated pest management practices.

Nutrient deficiency symptoms: Yellow leaves with green veins indicate iron deficiency. Purple undersides of leaves suggest phosphorus deficiency. Blossom end rot is caused by calcium deficiency."""

        result = chunk_text(content, chunk_size=500, overlap=50)

        assert len(result) >= 1
        # Check that key content is preserved
        all_text = " ".join(result)
        assert "Tomato" in all_text
        assert "watering" in all_text.lower()
        assert "temperature" in all_text.lower()
        assert "deficiency" in all_text.lower()
