"""Unit tests for built-in RAG template documents."""

from __future__ import annotations

from app.services.rag.templates import load_ukrainian_greenhouse_templates


def test_loads_10_ukrainian_greenhouse_templates() -> None:
    templates = load_ukrainian_greenhouse_templates()

    assert len(templates) == 10
    assert all(template.metadata["language"] == "uk" for template in templates)
    assert all(template.metadata["collection"] == "ukrainian-greenhouse-research" for template in templates)
    assert all(template.source_url.startswith("builtin://rag/ukrainian-greenhouse-research/") for template in templates)
    assert any("томат" in template.content.lower() for template in templates)
    assert any("огір" in template.content.lower() for template in templates)
    assert all("тепли" in template.content.lower() for template in templates)
