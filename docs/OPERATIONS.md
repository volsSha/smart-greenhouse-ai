# Operations

## Local services

Start dependencies with:

```bash
docker compose up -d
```

Expected services:

- Mosquitto MQTT on `1883`
- PostgreSQL with pgvector on `5432`
- InfluxDB on `8086`
- Grafana on `3000`

## App startup

Run migrations before starting the app:

```bash
uv run alembic upgrade head
uv run python -m app.main
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

1. Open `/` and confirm dashboard cards render.
2. Open `/rag`, add/search knowledge, and verify source attribution.
3. Open `/ai-chat`, ask for scoped greenhouse status, and inspect tool traces.
4. Open `/control`, verify proposal cards show approval/rejection actions.
5. Open `/logs`, filter recent alerts and command lifecycle records.
6. Confirm dependency outages surface through `/health/ready` rather than silent success.
