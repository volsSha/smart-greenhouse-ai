# Smart Greenhouse Management

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

## UI flows

Implemented page, button, simulator, control-panel, AI chat, settings, and observability flows are documented in `docs/ui-flows/README.md`.

## Localization

The UI supports English and Ukrainian through gettext catalogs in `locales/`. After changing user-facing text, extract/update translations and compile catalogs:

```bash
uv run pybabel extract -F babel.cfg -o locales/messages.pot app
uv run pybabel update -i locales/messages.pot -d locales
uv run pybabel compile -d locales
```

## Model Settings

The application includes a model settings page at `/settings` where you can:

- **Select Chat Model**: Choose from the OpenRouter model catalog for AI chat
- **View Embedding Configuration**: See the fixed embedding model (changing requires RAG reindex)
- **Manage Catalog**: Refresh the OpenRouter model catalog, search/filter by provider and capability
- **View Pricing**: See prompt and completion prices per million tokens for each model
- **Set Control Mode**: Choose whether approved commands execute through MQTT remote devices or the internal simulator

The selected chat model is stored in the database and used for all AI chat requests. If the selected model becomes unavailable, the AI will block with a clear error message. The selected control mode is also stored in the database and is read by `/settings`, `/simulator`, `/control`, and command execution.

## Safety model

AI and the control engine may create scoped command proposals only. Physical actuator commands are published to MQTT only after user approval, deterministic safety revalidation, and transition through `CommandService` and `CommandPublisher`.

## Testing

```bash
uv run pytest
```

See `docs/TESTING.md` and `docs/OPERATIONS.md` for test tiers, service checks, and manual verification steps.
