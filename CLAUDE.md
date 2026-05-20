# Smart Greenhouse AI

NiceGUI + FastAPI greenhouse app with English/Ukrainian i18n, MQTT, InfluxDB, PostgreSQL+pgvector.

Key paths: `app/` source; `app/ui/pages/` pages; `app/ui/components/` components; `app/i18n/core.py` gettext helpers; `locales/` catalogs; `docs/solutions/` past problem writeups; `Dockerfile` production; `Dockerfile.dev` dev; `compose.override.yml` dev mounts.

Workflow: run Python commands with `uv`. Rebuild/start dev app with `docker compose up -d --build app`. Source edits hot-reload. After `.po` edits run `pybabel compile -d locales`. Production uses `Dockerfile`.

Conventions: NiceGUI language switcher uses label-to-code `ui.select`; translatable components call `_()` from `app.i18n.core` at render time; all user-facing UI text needs English and Ukrainian translations; `ui.run_with(...)` needs real `storage_secret` for `app.storage.user`.

Debugging: check `/logs` first. For AI failures inspect `debug_log` rows `level="error"`, `component="ai_agent"`, `event_type="ai_chat_failed"`, then correlate with conversation messages and `ai_tool_calls`.

App-wide testing: use `docs/APP_TEST_CHECKLIST.md`. Production app-wide tests must verify through deployed domain/nginx; localhost/internal Docker only diagnostics.
