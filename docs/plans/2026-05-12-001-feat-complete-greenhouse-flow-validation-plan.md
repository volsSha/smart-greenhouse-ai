---
title: feat: Complete Greenhouse Flow Validation
type: feat
status: active
date: 2026-05-12
---

# feat: Complete Greenhouse Flow Validation

## Summary

Complete the unfinished UI/API seams needed for the current greenhouse demo flow, then verify the app end-to-end through browser tests before opening a PR.

---

## Problem Frame

The current branch adds simulator, MQTT, OpenRouter model settings, RAG, i18n, and AI chat surfaces, but some browser-requested flows are incomplete or unverified. The LFG run should turn the branch into a shippable PR by closing obvious functional gaps and validating each main page.

---

## Assumptions

*This plan was authored without synchronous user confirmation. The items below are agent inferences that fill gaps in the input — un-validated bets that should be reviewed before implementation proceeds.*

- The primary goal is shipping the current branch, not adding a new product track beyond requested page functionality.
- Browser verification should use Docker Compose development runtime on port `8080` unless implementation discovers a different exposed app port.
- RAG “file upload and rerank” means adding a UI-level file ingestion path and a search result ordering check using existing RAG storage/search APIs, not introducing a separate reranker service unless existing code already provides one.
- “Gemini Lite model” means selecting a Gemini-flavored OpenRouter catalog entry from settings when available; if unavailable, the UI should surface catalog absence clearly instead of hardcoding an unavailable model.

---

## Requirements

- R1. Settings page lets a user refresh/fetch OpenRouter catalog data, choose a chat model from available models, persist the selection, and reload with that selected model visible.
- R2. Settings page supports selecting a Gemini Lite/Gemini lightweight model when it exists in the catalog and fails clearly when the catalog lacks it.
- R3. Simulator page can start internal simulation, update running status, show animated zone visualization, and stop cleanly.
- R4. Dashboard shows simulator-generated fleet statistics and greenhouse cards after simulation has produced telemetry, and greenhouse card clicks reveal zone details.
- R5. AI chat page accepts a scoped greenhouse question and renders either an AI answer with tool transparency/proposed actions or a clear configuration/API error.
- R6. RAG page supports adding knowledge content, file-backed ingestion if missing, reindexing, searching, and verifying result order/score display.
- R7. All main NiceGUI pages render without visible server/UI errors: `/dashboard`, `/simulator`, `/plants`, `/control`, `/ai-chat`, `/rag`, `/logs`, `/settings`.
- R8. Relevant unit/integration tests cover newly completed behavior before browser verification.

---

## Scope Boundaries

- Do not redesign page navigation or the NiceGUI layout shell.
- Do not replace OpenRouter, PostgreSQL/pgvector, InfluxDB, MQTT, or NiceGUI architecture.
- Do not perform destructive database operations.
- Do not make real actuator side effects outside the existing proposal/approval safety model.
- Do not require a specific paid model to be present in a real OpenRouter account for automated tests.

### Deferred to Follow-Up Work

- Full production-grade RAG reranking service: defer unless an existing reranking hook is already present.
- Visual pixel-perfect polish beyond verifying animations render and controls work.
- Authentication/authorization: outside current project scope.

---

## Context & Research

### Relevant Code and Patterns

- `app/main.py` registers FastAPI routers, imports NiceGUI pages, redirects `/` to `/dashboard`, and mounts NiceGUI with `ui.run_with`.
- `app/ui/layouts/main_layout.py` defines navigation links for dashboard, simulator, plants, control, AI chat, RAG, logs, and settings.
- `app/ui/pages/settings.py` already loads `/api/settings` and `/api/settings/catalog`, but model selection is a placeholder.
- `app/api/settings.py` validates selected chat model against the stored catalog before persisting it.
- `app/ui/pages/simulator.py` controls `/api/simulator/start`, `/api/simulator/stop`, mode switching, status badges, and `ZoneVisualization` polling.
- `app/ui/pages/dashboard.py` reads telemetry summaries/latest data, renders greenhouse cards, and reveals zone details on greenhouse click.
- `app/ui/pages/rag.py` supports manual document creation, reindexing, and semantic search, but does not yet expose file upload in the UI.
- `app/api/rag.py` chunks, embeds, persists, reindexes, and searches documents through existing RAG services.
- `app/ui/pages/ai_chat.py` posts to `/api/ai/chat`, supports greenhouse scope fields, renders assistant responses, tool calls, and proposed actions.
- `docs/ROUTES.md` documents expected API and UI routes.

### Institutional Learnings

- `docs/solutions/developer-experience/nicegui-fastapi-dev-docker-hot-reload-2026-05-11.md` says dev Docker should use `Dockerfile.dev`, mounted `app/` and `locales/`, and port `8080`.
- `docs/solutions/ui-bugs/nicegui-i18n-docker-hot-reload-2026-05-11.md` says NiceGUI `ui.select` emits display labels in some patterns; map labels to canonical values and ensure a real `storage_secret` for persistence.

### External References

- External research skipped: current codebase has direct local patterns for NiceGUI pages, FastAPI routers, OpenRouter settings APIs, and RAG service calls.

---

## Key Technical Decisions

- Extend existing NiceGUI pages instead of adding alternate routes: keeps browser validation aligned with documented navigation.
- Use existing REST APIs for UI completion where possible: avoids duplicating persistence logic in page code.
- Keep model selection catalog-driven: prevents hardcoding provider/model IDs that may not exist in a user’s OpenRouter catalog.
- Keep file ingestion on top of existing `RAGDocumentCreate` semantics unless backend multipart upload is already needed: minimizes schema expansion and reuses chunk/embed flow.
- Treat browser tests as acceptance verification, not replacement for unit tests: newly completed behaviors still need targeted tests in `tests/unit/` or `tests/integration/`.

---

## Open Questions

### Resolved During Planning

- Should the LFG run start from a plan? Resolution: yes; LFG requires a durable plan before implementation.
- Which pages are in scope? Resolution: all main NiceGUI navigation pages, with deeper checks for settings, simulator/dashboard, AI chat, and RAG.

### Deferred to Implementation

- Exact `agent-browser` element refs: depend on rendered DOM after app starts.
- Whether real OpenRouter credentials are present: determine during runtime; missing credentials should be reported clearly rather than blocking local UI fixes.
- Whether simulator telemetry appears immediately in InfluxDB: verify during browser testing and adjust waits or ingestion fixes only if needed.

---

## Implementation Units

- U1. **Complete settings model selection**

**Goal:** Let users select a catalog model, persist it through `/api/settings`, and see the saved model after reload.

**Requirements:** R1, R2, R8

**Dependencies:** None

**Files:**
- Modify: `app/ui/pages/settings.py`
- Test: `tests/unit/test_openrouter_models.py`
- Test: `tests/unit/test_config.py`

**Approach:**
- Replace placeholder selection behavior with a catalog-driven selector or table interaction that keeps selected model ID in page state.
- Persist through the existing `PUT /api/settings` contract.
- Refresh current settings after save so the saved model label reflects database state.
- Keep provider/search/capability filters working while preserving the selected row/model state clearly.

**Patterns to follow:**
- `app/ui/pages/settings.py` existing `api_client`, `response_error`, status container, and loading patterns.
- `app/api/settings.py` existing model validation and response schemas.

**Test scenarios:**
- Happy path: catalog contains a Gemini lightweight model; selecting it and saving sends selected model ID to settings API and updates current settings display.
- Happy path: catalog contains another model; selecting and saving persists it without requiring provider-specific hardcoding.
- Edge case: no model selected; save control is disabled or warns without sending invalid API request.
- Error path: settings API rejects unavailable model; page surfaces the error and keeps previous selection visible.
- Integration: refreshed catalog followed by model selection uses freshly loaded catalog entries.

**Verification:**
- Browser can refresh catalog, choose a model, save it, reload `/settings`, and see the model retained.

---

- U2. **Add RAG file ingestion flow**

**Goal:** Let users upload or paste file-backed knowledge, create a RAG document, reindex/search it, and inspect ordered results.

**Requirements:** R6, R8

**Dependencies:** None

**Files:**
- Modify: `app/ui/pages/rag.py`
- Modify if needed: `app/api/rag.py`
- Modify if needed: `app/schemas/rag.py`
- Test: `tests/unit/test_rag_search_tool.py`
- Test: `tests/integration/test_ai_conversation_persistence.py`

**Approach:**
- Prefer a NiceGUI upload/text extraction UI that submits content through existing document creation semantics.
- Store uploaded file title/source type consistently with manual documents.
- Keep reindex and search controls visible after upload.
- Show search scores/order exactly enough for browser verification to confirm highest-ranked content appears first.

**Patterns to follow:**
- `app/ui/pages/rag.py` notification and document list reload patterns.
- `app/api/rag.py` chunk/embed/create/reindex/search flow.

**Test scenarios:**
- Happy path: uploading a text file creates a document with file source type and displays it in the document list.
- Happy path: searching for a phrase from the uploaded file returns that document in results with a score.
- Edge case: empty uploaded file or empty pasted content warns and does not call document creation.
- Error path: embedding service failure during document creation surfaces a negative notification/API error.
- Integration: create document, reindex, search, and confirm result ordering follows repository search score ordering.

**Verification:**
- Browser can upload file content, reindex/search, and see relevant result above unrelated content.

---

- U3. **Harden simulator-to-dashboard demo path**

**Goal:** Ensure simulation start produces visible running state, animated zone visualization, dashboard statistics, and clickable greenhouse details.

**Requirements:** R3, R4, R8

**Dependencies:** None

**Files:**
- Modify if needed: `app/ui/pages/simulator.py`
- Modify if needed: `app/ui/pages/dashboard.py`
- Modify if needed: `app/ui/components/zone_visualization.py`
- Modify if needed: `app/ui/components/telemetry_cards.py`
- Test: `tests/unit/test_simulator_page.py`
- Test: `tests/unit/test_zone_visualization.py`
- Test: `tests/unit/test_telemetry_schema.py`

**Approach:**
- Preserve existing simulator API calls and polling, fixing only gaps found during implementation/browser checks.
- Ensure start/stop buttons, status badge, message count, and zone visualization state move together.
- Ensure dashboard empty state guides user to simulator, and populated state renders greenhouse cards that reveal zone detail on click.

**Patterns to follow:**
- `app/ui/pages/simulator.py` `ui.timer` polling and `_update_status` state synchronization.
- `app/ui/pages/dashboard.py` transform functions and greenhouse-card click binding.

**Test scenarios:**
- Happy path: start simulator response marks status running, disables start, enables stop, and activates polling.
- Happy path: zone data response updates visualization and hides no-data label.
- Happy path: dashboard latest readings transform into greenhouse cards and group stats.
- Edge case: no telemetry shows empty state with simulator guidance.
- Error path: simulator start failure leaves stopped state and shows clear error.
- Integration: clicking a greenhouse card after telemetry loads reveals zone detail cards and chart area.

**Verification:**
- Browser can start simulator, observe animation/zone state, open dashboard, see stats/cards, click greenhouse, and see zone details.

---

- U4. **Verify AI chat greenhouse question flow**

**Goal:** Ensure a scoped greenhouse question produces a visible assistant response or actionable configuration error without breaking page state.

**Requirements:** R5, R8

**Dependencies:** U1 if selected model is required for successful AI response.

**Files:**
- Modify if needed: `app/ui/pages/ai_chat.py`
- Modify if needed: `app/api/ai_chat.py`
- Modify if needed: `app/services/ai_agent/agent.py`
- Test: `tests/unit/test_ai_read_only_tools.py`
- Test: `tests/integration/test_ai_conversation_persistence.py`

**Approach:**
- Keep existing chat API and rendering contract.
- Ensure group/greenhouse/zone scope fields are sent in the payload.
- Preserve visible loading/error states and conversation refresh after response.
- If credentials/model selection are missing, surface the existing configuration error clearly.

**Patterns to follow:**
- `app/ui/pages/ai_chat.py` `_build_scope_dict`, loading container, and assistant/proposed-action rendering.
- `app/services/ai_agent/tools/greenhouse_tools.py` and related read-only tool tests.

**Test scenarios:**
- Happy path: question with `group-001` and greenhouse scope posts expected scope and renders assistant summary.
- Happy path: response with observations/recommendations/tool calls renders corresponding UI panels.
- Edge case: empty message does not call API.
- Error path: missing model/API configuration shows request failure detail and re-enables send.
- Integration: successful response appears in conversation list and can be reloaded.

**Verification:**
- Browser can ask about a greenhouse and see either an answer/tool trace or a clear configuration error with no stuck loading state.

---

- U5. **Run full page browser acceptance sweep**

**Goal:** Validate the branch through visible or headless browser flows and capture failures before PR creation.

**Requirements:** R1, R2, R3, R4, R5, R6, R7

**Dependencies:** U1, U2, U3, U4

**Files:**
- Modify if needed: files implicated by browser failures
- Test expectation: none -- this unit is browser acceptance verification and targeted fixes are covered by their owning units.

**Approach:**
- Start Docker Compose app using the dev container pattern.
- Test `/dashboard`, `/simulator`, `/plants`, `/control`, `/ai-chat`, `/rag`, `/logs`, `/settings`.
- Exercise critical interactions: settings catalog/model save, simulator start/stop, dashboard greenhouse click, AI chat question, RAG upload/search/reindex, language/navigation sanity.
- Record external-service blockers explicitly when they depend on credentials or upstream availability.

**Patterns to follow:**
- `docs/solutions/developer-experience/nicegui-fastapi-dev-docker-hot-reload-2026-05-11.md` Docker dev runtime guidance.
- `docs/ROUTES.md` route list.

**Test scenarios:**
- Browser route sweep: every main route loads with expected heading/navigation and no visible server error.
- Browser settings flow: refresh/fetch catalog, select model, save, reload, confirm selection.
- Browser simulator/dashboard flow: start simulator, observe running/animation, navigate to dashboard, verify stats and greenhouse click detail.
- Browser RAG flow: upload/add document, reindex, search, verify ranked result display.
- Browser AI flow: ask greenhouse question with scope, verify response or clear configuration error.

**Verification:**
- Browser test summary reports pass/fail/partial with concrete blockers and screenshots only when useful.

---

## System-Wide Impact

- **Interaction graph:** NiceGUI pages call FastAPI APIs through `app/ui/api_client.py`; simulator and dashboard depend on telemetry services; AI chat and RAG depend on OpenRouter configuration.
- **Error propagation:** API errors should remain visible as page notifications/labels and must not leave buttons disabled or loading states stuck.
- **State lifecycle risks:** Settings selection must round-trip through database state; simulator timers must not keep stale running UI after stop/failure; RAG upload should not show success until persistence succeeds.
- **API surface parity:** Keep documented routes in `docs/ROUTES.md` accurate if any API changes are required.
- **Integration coverage:** Browser acceptance is required because NiceGUI event wiring and visible state cannot be fully proven by pure unit tests.
- **Unchanged invariants:** Command approval safety model, embedding model immutability warning, and existing route names remain unchanged.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| OpenRouter API credentials or upstream model availability are missing during local testing | Treat as external blocker only after UI/API error handling is verified; avoid hardcoding unavailable models. |
| RAG embedding calls need live external service | Keep UI behavior testable through visible errors and use existing unit/integration seams where possible. |
| Simulator telemetry may lag before dashboard data appears | Browser test should wait/poll long enough to distinguish ingestion delay from failure. |
| NiceGUI event value behavior differs from assumed IDs/labels | Follow existing language switcher learning: map display labels to stable model IDs explicitly. |
| Docker app may not be running at expected port | Use documented dev port `8080`, then inspect Compose output if unavailable. |

---

## Documentation / Operational Notes

- Update `docs/ROUTES.md` only if route/API behavior changes.
- Do not commit generated screenshots unless explicitly needed for PR evidence.
- If `.po` files change, compile catalogs before final verification.

---

## Sources & References

- Related code: `app/ui/pages/settings.py`
- Related code: `app/ui/pages/simulator.py`
- Related code: `app/ui/pages/dashboard.py`
- Related code: `app/ui/pages/rag.py`
- Related code: `app/ui/pages/ai_chat.py`
- Related code: `app/api/settings.py`
- Related code: `app/api/rag.py`
- Related docs: `docs/ROUTES.md`
- Institutional learning: `docs/solutions/developer-experience/nicegui-fastapi-dev-docker-hot-reload-2026-05-11.md`
- Institutional learning: `docs/solutions/ui-bugs/nicegui-i18n-docker-hot-reload-2026-05-11.md`
