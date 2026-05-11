# Residual Review Findings

Source: LFG code review autofix run for `docs/plans/2026-05-12-001-feat-complete-greenhouse-flow-validation-plan.md` on branch `fix/Volodymyr/agents-flow`.

## Residual Review Findings

- P1 `app/ui/pages/settings.py`: Settings page model-selection workflow lacks UI-level tests for catalog rendering, selecting Gemini/lightweight model, enabling save, PUT `/api/settings`, reload persistence, no-selection warning, and rejected-model error handling. No tracker ticket filed; this fallback file is the durable record.
- P1 `app/ui/pages/rag.py`: RAG upload path lacks UI-level tests for decoding uploaded file content, filling title/source type/content, posting `/api/rag/documents`, reloading documents, empty-file handling, and embedding/API failure handling. No tracker ticket filed; this fallback file is the durable record.
- P2 `app/ui/pages/rag.py`: RAG search result ordering/score display lacks UI-level tests for preserving API result order and rendering score labels. No tracker ticket filed; this fallback file is the durable record.
- P2 `app/ui/pages/settings.py`: Catalog refresh UI lacks tests for success reload, non-success payload, HTTP error retry state, and refresh button re-enable behavior. No tracker ticket filed; this fallback file is the durable record.
