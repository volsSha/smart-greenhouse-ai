# Tech Stack

## Core Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| UI | **NiceGUI** | Group dashboard, greenhouse/zone views, chat, simulator, controls |
| Backend API | **FastAPI** | REST, WebSocket, AI tools, command routing, safety layer |
| MQTT broker | **Mosquitto** | Scoped telemetry and command exchange |
| Time-series | **InfluxDB** | Microclimate telemetry across groups, greenhouses, zones, sensors |
| Relational DB | **PostgreSQL** | Groups, greenhouses, zones, devices, plants, settings, commands, AI logs |
| Vector search | **pgvector** | RAG for plant knowledge, care rules, system docs |
| LLM provider | **OpenRouter** | LLM reasoning, explanations, proposed actions |
| Agent framework | **Pydantic AI** | Tool calling, structured output, deferred/approval-required proposed action tools |
| Control | **Python rules first; PID/Fuzzy later** | Baseline observer/proposer; advanced autonomous tuning deferred |
| Containers | **Docker Compose** | Single repository, single startup |

## Component Roles

| Component | Role |
|-----------|------|
| NiceGUI | Human-machine interface for group, greenhouse, and zone operations |
| FastAPI | Central logic, API, tools, safety validation, command routing |
| Mosquitto | Telemetry/command transport with topic ACLs |
| InfluxDB | Scoped time-series telemetry |
| PostgreSQL | Fleet structure, devices, plant batches, policies, commands, logs |
| pgvector | RAG memory for agronomic knowledge |
| OpenRouter | LLM reasoning and explanations |
| Pydantic AI | Agent loop, tool approval, structured responses, deterministic tests |
| Control Engine | Rule-based observer/proposer for zone and group conditions |
| Simulator | Virtual edge nodes for multiple greenhouses/zones |

## Python Dependencies

### Base

```text
fastapi
uvicorn[standard]
nicegui
pydantic
pydantic-settings
sqlalchemy
alembic
asyncpg
psycopg[binary]
pgvector
influxdb-client
paho-mqtt
aiomqtt
numpy
pandas
plotly
python-dotenv
httpx
pytest
pytest-asyncio
```

### AI / RAG

```text
pydantic-ai
tiktoken
```

OpenRouter is used as an OpenAI-compatible API endpoint through Pydantic AI / HTTP client configuration, so the default dependency path does **not** require the standalone `openrouter` package. If implementation chooses the standalone OpenRouter SDK instead of Pydantic AI provider configuration, add `openrouter` deliberately and update the agent plan.

Embedding dependency depends on the chosen provider:
- API embeddings with 1536 dimensions: no local `sentence-transformers` dependency required
- local embeddings: add `sentence-transformers` and update pgvector dimensions before first migration

## Install with uv

### Runtime dependencies

```bash
uv add fastapi 'uvicorn[standard]' nicegui pydantic pydantic-settings sqlalchemy alembic asyncpg 'psycopg[binary]' pgvector influxdb-client paho-mqtt aiomqtt numpy pandas plotly python-dotenv httpx pydantic-ai tiktoken
```

### Test dependencies

```bash
uv add --dev pytest pytest-asyncio
```

### Optional local embeddings

Only run this if choosing local embeddings instead of API embeddings:

```bash
uv add sentence-transformers
```

### Deferred advanced control

Only run this when implementing PID/fuzzy autonomous control:

```bash
uv add simple-pid scikit-fuzzy
```

### Standalone OpenRouter SDK alternative

Only run this if not using Pydantic AI's OpenAI-compatible provider configuration for OpenRouter:

```bash
uv add openrouter
```

### Deferred / Later

```text
simple-pid
scikit-fuzzy
```

Add these only when implementing advanced autonomous control. The initial system uses rule-based observation and proposed actions.

## Infrastructure Images

| Service | Image | Local port |
|---------|-------|------------|
| Mosquitto | eclipse-mosquitto:2.1.2-alpine | 11883, 19001 |
| PostgreSQL | pgvector/pgvector:0.8.2-pg17-trixie | 5432 |
| InfluxDB | influxdb:2.7.12 | 8086 |
| Grafana | grafana/grafana:13.0.1 | 3000 |

Pin exact image tags in Docker Compose. Do not use floating `latest` for stateful services. Related troubleshooting: `docs/solutions/ui-bugs/docker-compose-fastapi-nicegui-dashboard-launch-fix-2026-05-07.md` documents the verified local Compose image set, pgvector init, and NiceGUI dashboard launch fix.
