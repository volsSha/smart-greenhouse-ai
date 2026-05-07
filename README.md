# Smart Greenhouse Fleet Control

FastAPI, NiceGUI, MQTT, PostgreSQL/pgvector, InfluxDB, and AI-assisted greenhouse fleet monitoring.

## Quick start

1. Copy `.env.example` to `.env` and fill local development values.
2. Start infrastructure with Docker Compose:

```bash
docker compose up -d
```

3. Run migrations:

```bash
uv run alembic upgrade head
```

4. Start the app:

```bash
uv run python -m app.main
```

5. Publish sample telemetry:

```bash
uv run python -m services.simulator.main --once
```

## Main entry points

- API and UI: `uv run python -m app.main`
- MQTT simulator: `uv run python -m services.simulator.main`
- RAG worker: `uv run python -m services.worker.main --job rag-reindex`
- Baseline control observer: `uv run python -m services.control_engine.main --group-id <uuid> --greenhouse-id <uuid> --zone-id <uuid> --soil-moisture 18`

## Safety model

AI and the control engine may create scoped command proposals only. Physical actuator commands are published to MQTT only after user approval, deterministic safety revalidation, and transition through `CommandService` and `CommandPublisher`.

## Testing

```bash
uv run pytest
```

See `docs/TESTING.md` and `docs/OPERATIONS.md` for test tiers, service checks, and manual verification steps.
