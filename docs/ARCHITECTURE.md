# Smart Greenhouse AI - Architecture

## Core Idea

LLM does not directly control the greenhouse. It is an intelligence layer that:

1. Accepts natural language user requests
2. Decides which tools to call
3. Retrieves data from InfluxDB / PostgreSQL / RAG
4. Analyzes plant state
5. Generates explanations and recommendations
6. For control actions, creates an **intent** that passes through safety validation
7. Only after validation does the command go to MQTT

## System Diagram

```
                         +----------------------+
                         |      NiceGUI UI       |
                         | dashboard / chat /    |
                         | simulator / controls  |
                         +----------+-----------+
                                     | HTTP / WS
                                     v
+---------------------+    +----------------------+
| Sensor Simulator    |    |      FastAPI API      |
| virtual ESP32       |    | auth / commands /     |
| publishes telemetry |    | telemetry / tools     |
+----------+----------+    +-------+-------+------+
           | MQTT                  |       |
           v                       |       |
+---------------------+            |       |
| Mosquitto MQTT      |<-----------+       |
| broker              | commands           |
+----------+----------+                    |
           | telemetry                   |
           v                             v
+---------------------+          +----------------------+
| Control Engine      |          | PostgreSQL + pgvector |
| PID / Fuzzy / rules |          | plants / users /      |
| publishes commands  |          | AI logs / RAG         |
+----------+----------+          +----------------------+
           |
           v
+---------------------+
| InfluxDB            |
| time-series telemetry|
+---------------------+

                  +------------------------+
                  | OpenRouter AI Agent    |
                  | tool calling + RAG     |
                  +------------------------+
```

## Architecture Pattern

Monorepo with clear service boundaries - single repository, clean separation of concerns.

```
smart-greenhouse-ai/
|
+-- docker-compose.yml
+-- .env.example
+-- pyproject.toml
+-- README.md
|
+-- services/
|   +-- api/                 # FastAPI backend
|   +-- ui/                  # NiceGUI web app
|   +-- simulator/           # MQTT sensor simulator
|   +-- control_engine/      # PID / Fuzzy controller
|   +-- ai_agent/            # OpenRouter agent + tools
|   +-- worker/              # background jobs: embeddings, summaries, reports
|
+-- packages/
|   +-- shared/              # shared schemas, MQTT topics, constants
|   +-- db/                  # SQLAlchemy models, migrations
|   +-- telemetry/           # InfluxDB client, queries
|   +-- rag/                 # pgvector retrieval logic
|   +-- greenhouse_rules/    # plant thresholds, safety rules
|
+-- infra/
|   +-- mosquitto/
|   +-- postgres/
|   +-- influxdb/
|   +-- grafana/
|
+-- migrations/
|   +-- alembic/
|
+-- tests/
```

## Database Roles

### InfluxDB - Telemetry Only

High-frequency time series: temperature, air_humidity, co2, light, soil_moisture, fan_power, pump_state, heater_power, lamp_state.

Measurement format:
- measurement: `greenhouse_telemetry`
- tags: greenhouse_id, sensor_id, metric
- fields: value, quality
- time: timestamp

### PostgreSQL - Structured Business Data

Users, greenhouses, plants, plant profiles, control setpoints, commands, events, alerts, AI chats, tool calls, RAG documents, embeddings via pgvector.

## LLM Agent Interaction Model

**Correct:** LLM Agent -> structured intent -> FastAPI validates -> MQTT command

**Wrong:** LLM Agent -> MQTT command directly

## Safety Layer

All control actions pass through validation before execution:

```python
SAFETY_LIMITS = {
    "pump": {"max_duration_seconds": 60, "cooldown_seconds": 300},
    "fan": {"max_power": 100, "max_duration_seconds": 600},
    "heater": {"max_power": 80, "max_duration_seconds": 300, "forbidden_if_temperature_above": 28},
    "lamp": {"max_duration_seconds": 3600},
}
```

## Full Data Flow: Sensor to AI Response

1. Simulator publishes telemetry via MQTT
2. API / telemetry worker writes to InfluxDB
3. Control engine checks rules (e.g. soil_moisture < 25% -> alert + propose pump)
4. User asks AI: "How are my plants?"
5. AI calls tools: get_plants, get_today_telemetry_summary, get_active_alerts, get_plant_profile, search_plant_knowledge
6. AI responds with analysis based on real data
7. AI creates proposed action (e.g. water for 30 sec)
8. Backend validates the command
9. User confirms -> command goes to MQTT
