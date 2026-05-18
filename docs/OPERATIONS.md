# Operations

## Production deployment

Production Docker deployment lives in `deploy/production/`. See `deploy/production/README.md` for the server `.env`, Docker nginx, TLS/access gate, Mosquitto credentials, backup, migration, and remote deployment workflow for `greenhouse.volsh.dev`.

## Local services

Start dependencies with:

```bash
docker compose up -d
```

Expected services:

- App on `8080`
- Mosquitto MQTT on `11883` and WebSocket on `19001`
- PostgreSQL with pgvector on `5432`
- InfluxDB on `8086`

## App startup

Run migrations before starting the app:

```bash
uv run alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080
```

The FastAPI lifespan initializes SQLAlchemy, InfluxDB, and telemetry repositories. MQTT clients are created on demand.

## Simulator

Publish one telemetry burst:

```bash
uv run python -m services.simulator.main --once
```

Run a scenario loop:

```bash
uv run python -m services.simulator.main --scenario dry_soil --interval 5
```

## Worker

Reindex stale RAG documents:

```bash
uv run python -m services.worker.main --job rag-reindex
```

Reindex all documents:

```bash
uv run python -m services.worker.main --job rag-reindex --all
```

## Control engine

The baseline control engine observes telemetry-shaped inputs and creates command proposals. It does not publish MQTT commands directly.

```bash
uv run python -m services.control_engine.main --group-id <uuid> --greenhouse-id <uuid> --zone-id <uuid> --soil-moisture 18
```

## Manual verification

1. Open `/` and confirm it redirects to `/dashboard`, then confirm dashboard cards render.
2. Open `/settings`, switch control mode, save it, and verify `/simulator` and `/control` reflect the selected mode.
3. Open `/simulator`, start the internal simulator in simulator mode, verify live zone cards update, then stop it.
4. Open `/zones`, select group/greenhouse scope, create or inspect a zone, and verify the displayed MQTT topic matches firmware config expectations.
5. Open `/control`, select group/greenhouse/zone, create a command proposal, then approve or reject it.
6. Open `/ai-chat`, ask for scoped greenhouse status, inspect tool traces, and verify any proposed action card requires approval.
7. Open `/rag`, add/search knowledge, and verify source attribution.
8. Open `/logs`, filter recent alerts and command lifecycle records.
9. Confirm dependency outages surface through `/health/ready` rather than silent success.

Detailed arrow-style UI flows are in `docs/ui-flows/README.md`.

Related troubleshooting: `docs/solutions/ui-bugs/docker-compose-fastapi-nicegui-dashboard-launch-fix-2026-05-07.md` documents the verified Docker Compose and FastAPI/NiceGUI launch fixes.
