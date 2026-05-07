---
title: "Docker Compose FastAPI NiceGUI Dashboard Launch Fix"
date: 2026-05-07
category: "docs/solutions/ui-bugs/"
module: "docker-compose / FastAPI / NiceGUI"
problem_type: ui_bug
component: tooling
symptoms:
  - "Docker Compose stack had launch blockers across Mosquitto, InfluxDB, Grafana, PostgreSQL, and the app container."
  - "FastAPI root path / returned Not Found instead of opening the dashboard."
  - "NiceGUI dashboard returned HTTP 500 with AttributeError: module nicegui.ui has no attribute 'sidebar'."
root_cause: wrong_api
resolution_type: code_fix
severity: medium
tags:
  - docker-compose
  - fastapi
  - nicegui
  - pgvector
  - grafana
  - influxdb
  - mosquitto
---

# Docker Compose FastAPI NiceGUI Dashboard Launch Fix

## Problem

The local Smart Greenhouse Docker Compose stack had multiple service startup blockers, and after the stack became healthy the app root still failed to open the dashboard. `/` returned 404 until a FastAPI redirect was added, and `/dashboard` returned 500 because the UI layout used a NiceGUI API removed in the installed version.

## Symptoms

- MQTT could not bind the default local `1883` port.
- Mosquitto failed when configured with a missing password file.
- InfluxDB `2.9.0` setup failed with `dasel` reporting a missing `http-bind-address` map key.
- The app container failed with `uvicorn` missing from `PATH`.
- Grafana 13 healthcheck failed because `grafana-cli` was unavailable.
- Grafana dashboard provisioning failed until dashboards were mounted at `/var/lib/grafana/dashboards`.
- `GET /` returned 404.
- `GET /dashboard` returned 500 with:

```text
AttributeError: module 'nicegui.ui' has no attribute 'sidebar'
```

- After registering all linked page modules, `/simulator` returned 500 because button callbacks referenced local handlers before assignment.

## What Didn't Work

- Publishing MQTT on host port `1883`; another local process could already own that port.
- Keeping Mosquitto `password_file` configuration without mounting the referenced password file.
- Using `influxdb:2.9.0`; it failed during first-run setup, while `influxdb:2.7.12` initialized successfully.
- Starting NiceGUI via `python -m app.main`; the app is designed to run under Uvicorn.
- Calling `ui.run(app=app, ...)`; NiceGUI does not accept that FastAPI mounting pattern.
- Keeping `ui.sidebar()` in `app/ui/layouts/main_layout.py`; the installed NiceGUI exposes `ui.left_drawer()` and `ui.drawer()`, not `ui.sidebar()`.
- Importing only some NiceGUI page modules; linked pages such as `/simulator` and `/plants` need their modules imported so decorators register.
- Passing locally defined simulator handlers directly before assignment; wrapper callbacks let button creation happen before the final handler bodies are defined.

## Solution

Pin the Docker stack to verified images and keep local-only port bindings in the Compose override:

```yaml
services:
  mosquitto:
    image: eclipse-mosquitto:2.1.2-alpine
  postgres:
    image: pgvector/pgvector:0.8.2-pg17-trixie
  influxdb:
    image: influxdb:2.7.12
  grafana:
    image: grafana/grafana:13.0.1
```

```yaml
# compose.override.yml
mosquitto:
  ports:
    - "127.0.0.1:11883:1883"
    - "127.0.0.1:19001:9001"
```

Enable pgvector for fresh PostgreSQL volumes with `infra/postgres/init/001-enable-vector.sql`:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Install app dependencies into a deterministic runtime virtual environment in `Dockerfile`:

```dockerfile
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
RUN uv sync --frozen --no-dev --no-install-project
ENV PATH="/opt/venv/bin:$PATH"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

Mount NiceGUI into FastAPI and redirect the root path in `app/main.py`:

```python
from fastapi.responses import RedirectResponse


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse("/dashboard")


from app.ui.pages import dashboard, settings, control, logs, ai_chat, rag, simulator, plants  # noqa: E402, F401
from nicegui import ui  # noqa: E402

ui.run_with(
    app,
    title="Smart Greenhouse Fleet",
    storage_secret="",
)
```

Replace the removed NiceGUI sidebar API in `app/ui/layouts/main_layout.py`:

```python
with ui.left_drawer().classes("p-4"):
    ui.label("Menu").classes("text-md font-bold mb-4")
```

Use wrapper callbacks in `app/ui/pages/simulator.py` when buttons are created before the final handler bodies:

```python
async def handle_start_simulator() -> None:
    await start_simulator()

ui.button("Start Simulator", on_click=handle_start_simulator)
```

Verify the app routes after restarting the app container:

```text
GET /api/health/live -> 200
GET / -> 200 after redirect to /dashboard
GET /dashboard -> 200 text/html; charset=utf-8
GET /simulator -> 200 text/html; charset=utf-8
GET /plants -> 200 text/html; charset=utf-8
```

## Why This Works

Pinning images removes ambiguity around upstream entrypoint and CLI changes. The pgvector init SQL makes the extension available for fresh PostgreSQL volumes. `UV_PROJECT_ENVIRONMENT=/opt/venv` ensures the runtime image contains the same virtual environment whose `uvicorn` binary is placed on `PATH`.

For the app, Uvicorn should load `app.main:app`; NiceGUI is mounted into that FastAPI app with `ui.run_with(app, ...)`. The explicit root route handles users opening the base URL, and `ui.left_drawer()` matches the installed NiceGUI API where `ui.sidebar()` no longer exists.

## Prevention

- Pin infrastructure image tags and verify first-run setup before treating a tag as safe.
- Keep developer-machine port bindings in `compose.override.yml` so the base Compose file stays portable.
- Use stable HTTP health endpoints instead of version-dependent CLI tools.
- For NiceGUI mounted into FastAPI, use `ui.run_with(app, ...)` and start the process with `uvicorn app.main:app`.
- Verify NiceGUI component APIs inside the container when upgrading or adding UI layout components.

## Related Issues

- Related operational docs: `docs/OPERATIONS.md`, `docs/STACK.md`, and `docs/ROUTES.md` now link or reflect this solution so stack startup and route troubleshooting are discoverable.
- `docs/plans/2026-05-07-001-feat-smart-greenhouse-final-app-plan.md` carries the resolved image tags and NiceGUI mounting convention forward for implementation work.
