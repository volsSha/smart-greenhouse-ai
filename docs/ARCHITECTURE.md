# Smart Greenhouse Fleet Control System - Architecture

## Core Idea

The system manages a **group of small greenhouses**, not one greenhouse. Each greenhouse can contain multiple zones, each zone has its own sensors, actuators, plant batches, setpoints, alerts, and telemetry stream.

The LLM does not directly control devices. It is an intelligence layer that:

1. Accepts natural language requests about a group, greenhouse, or zone
2. Decides which read-only tools to call
3. Retrieves data from InfluxDB / PostgreSQL / RAG
4. Analyzes zone, greenhouse, or group state
5. Generates explanations and recommendations
6. Creates proposed actions for a specific group/greenhouse/zone/actuator
7. Sends proposals through FastAPI safety validation and user approval
8. Only after validation and approval does the backend publish an MQTT command

## System Diagram

```text
                         +----------------------+
                         |      NiceGUI UI       |
                         | fleet dashboard /     |
                         | zones / chat / logs   |
                         +----------+-----------+
                                    | HTTP / WS
                                    v
+---------------------+    +-------------------------------+
| Edge Node /         |    |          FastAPI Backend        |
| Simulator gh-001    |    | group / greenhouse / zone /     |
| publishes telemetry |    | telemetry / commands / tools    |
+----------+----------+    +-------+---------+--------------+
           | MQTT                  |         |
+----------v----------+            |         |
| Edge Node /         |            |         |
| Simulator gh-002    |            |         |
+----------+----------+            |         |
           | MQTT                  |         |
           v                       |         v
+---------------------+            |  +----------------------+
| Mosquitto MQTT      |<-----------+  | PostgreSQL + pgvector |
| broker              | commands      | groups / greenhouses /|
+----------+----------+               | zones / devices / AI  |
           | telemetry                | logs / RAG            |
           v                          +----------------------+
+-----------------------------+
| Multi-Greenhouse Telemetry  |
| Aggregator                  |
+-------------+---------------+
              |
              v
+---------------------+
| InfluxDB            |
| microclimate        |
| time-series         |
+---------------------+

          +------------------------+
          | Pydantic AI +          |
          | OpenRouter Agent       |
          | tools + RAG            |
          +------------------------+
```

## Backend Components

```text
FastAPI Backend
  ├── Greenhouse Group Service
  ├── Greenhouse Service
  ├── Zone Service
  ├── Fleet Device Registry
  ├── Multi-Greenhouse Telemetry Aggregator
  ├── Command Routing Service
  ├── Group Policy Engine
  ├── Safety Validator
  ├── AI Tools API
  └── RAG Service
```

## Architecture Pattern

Monorepo with clear service boundaries. The web/API application can run as one integrated FastAPI + NiceGUI process, while simulators, control engine, and workers remain separate process entry points.

```text
smart-greenhouse-ai/
|
+-- docker-compose.yml
+-- .env.example
+-- pyproject.toml
+-- README.md
|
+-- app/                         # FastAPI + NiceGUI app
|   +-- api/                     # REST endpoints
|   +-- ui/                      # NiceGUI pages and components
|   +-- models/                  # SQLAlchemy models
|   +-- schemas/                 # Pydantic schemas
|   +-- repositories/            # PostgreSQL / InfluxDB access
|   +-- services/                # domain services, AI agent, RAG, MQTT
|   +-- core/                    # settings, topics, safety limits
|
+-- services/
|   +-- simulator/               # multi-greenhouse MQTT simulator
|   +-- control_engine/          # rule-based observer/proposer
|   +-- worker/                  # embeddings, summaries, reports
|
+-- infra/
|   +-- mosquitto/
|   +-- postgres/
|   +-- influxdb/
|
+-- migrations/
|   +-- alembic/
|
+-- tests/
```

## Domain Model

```text
GreenhouseGroup 1 ── 1..* Greenhouse
Greenhouse 1 ── 1..* GreenhouseZone
Greenhouse 1 ── 1..* EdgeNode
GreenhouseZone 1 ── 0..* Sensor
GreenhouseZone 1 ── 0..* Actuator
GreenhouseZone 1 ── 0..* PlantBatch
GreenhouseZone 1 ── 0..* ControlSetpoint
GreenhouseZone 1 ── 0..* Alert
GreenhouseZone 1 ── 0..* Command
GreenhouseGroup 1 ── 0..* GroupControlPolicy
```

## Database Roles

### InfluxDB - Microclimate Telemetry Only

High-frequency time series: temperature, air_humidity, co2, light, soil_moisture, fan_power, pump_state, heater_power, lamp_state.

Measurement format:
- measurement: `microclimate`
- tags: group_id, greenhouse_id, zone_id, sensor_id, metric
- fields: value, quality
- time: timestamp

### PostgreSQL - Structured Fleet Data

Groups, greenhouses, zones, edge nodes, sensor registry, actuator registry, plant batches, plant profiles, group policies, setpoints, commands, alerts, AI chats, tool calls, RAG documents, embeddings via pgvector.

## MQTT Topic Model

Prefer the readable topic hierarchy for clarity:

```text
greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/telemetry
greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/commands
greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/alerts
greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/state
```

Short practical aliases may be supported later:

```text
gh/{group_id}/{greenhouse_id}/{zone_id}/telemetry
gh/{group_id}/{greenhouse_id}/{zone_id}/commands
gh/{group_id}/{greenhouse_id}/{zone_id}/alerts
gh/{group_id}/{greenhouse_id}/{zone_id}/state
```

Example topics:

```text
greenhouse-groups/group-001/greenhouses/gh-001/zones/zone-01/telemetry
greenhouse-groups/group-001/greenhouses/gh-002/zones/zone-01/telemetry
greenhouse-groups/group-001/greenhouses/gh-002/zones/zone-02/commands
```

## LLM Agent Interaction Model

**Correct:** LLM Agent -> scoped proposed action -> FastAPI validates group/greenhouse/zone/action -> user approves -> MQTT command

**Wrong:** LLM Agent -> MQTT command directly

The AI can analyze three levels:

1. **Zone level** - "How are the tomatoes in greenhouse 2, zone 1?"
2. **Greenhouse level** - "How is greenhouse 2 today?"
3. **Group level** - "How are my greenhouses? Which one needs attention?"

## Safety Layer

All control actions are scoped to `group_id`, `greenhouse_id`, `zone_id`, and `actuator_id`. Safety validation checks zone state, greenhouse state, group policies, command cooldowns, and mutually unsafe actuator combinations before execution.

```python
SAFETY_LIMITS = {
    "pump": {"max_duration_seconds": 60, "cooldown_seconds": 300},
    "fan": {"max_power": 100, "max_duration_seconds": 600},
    "heater": {"max_power": 80, "max_duration_seconds": 300, "forbidden_if_temperature_above": 28},
    "lamp": {"max_duration_seconds": 3600},
}
```

## Full Data Flow: Sensor to Group AI Response

1. Edge node or simulator publishes scoped telemetry via MQTT
2. Backend subscriber validates `group_id`, `greenhouse_id`, `zone_id`, `sensor_id`, metric, value, quality, and timestamp
3. Backend writes telemetry to InfluxDB measurement `microclimate`
4. Telemetry aggregation updates zone, greenhouse, and group summaries
5. Rule engine checks zone rules, greenhouse rules, and group policies
6. User asks AI: "How are my greenhouses?"
7. AI calls tools: get_group_overview, get_today_group_summary, get_active_alerts, compare_greenhouses, search_plant_knowledge
8. AI responds with group-level summary and prioritized issues
9. AI creates a scoped proposed action, e.g. water `group-001 / gh-002 / zone-01` for 30 seconds
10. Backend validates the command against current zone telemetry, group policy, and actuator safety limits
11. User confirms -> backend publishes command to the scoped MQTT command topic
