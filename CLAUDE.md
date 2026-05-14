# Smart Greenhouse AI

## Project Overview

NiceGUI + FastAPI greenhouse fleet control app with i18n (English/Ukrainian), MQTT telemetry, InfluxDB time-series, and PostgreSQL+pgvector storage.

## Key Paths

- `app/` — application source (UI pages in `app/ui/pages/`, components in `app/ui/components/`)
- `app/i18n/` — gettext-backed translation helpers (`core.py`)
- `locales/` — `.po`/`.mo` translation catalogs; run `pybabel compile -d locales` after edits
- `docs/solutions/` — documented solutions to past problems (bugs, best practices, workflow patterns), organized by category with YAML frontmatter (`module`, `tags`, `problem_type`). Relevant when implementing or debugging in documented areas.
- `Dockerfile` — production image (multi-stage, non-root)
- `Dockerfile.dev` — development image (uvicorn --reload, dev deps)
- `compose.override.yml` — dev overrides: builds from Dockerfile.dev, mounts source volumes

## Dev Workflow

- `docker compose up -d --build app` — rebuild and start dev container
- Source edits in `app/` and `locales/` hot-reload via uvicorn --reload
- After `.po` edits, run `pybabel compile -d locales` then the container auto-reloads
- Production uses `Dockerfile` (not `Dockerfile.dev`)

## Conventions

- Language switcher uses `ui.select` with label-to-code mapping (NiceGUI select events emit display labels, not dict keys)
- NiceGUI components that need language must call `_()` from `app.i18n.core` at render time
- `ui.run_with(...)` requires a real `storage_secret` for `app.storage.user` persistence

## Debugging

- Check `/logs` first when debugging API, UI, or AI command failures; it displays persisted `debug_log` entries.
- For failed AI commands, inspect `debug_log` rows with `level="error"`, `component="ai_agent"`, and `event_type="ai_chat_failed"`.
- Correlate error-log entries with AI conversation messages and `ai_tool_calls` when the failure involves tool execution.