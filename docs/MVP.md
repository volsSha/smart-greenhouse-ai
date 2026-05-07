# MVP Roadmap

## MVP 1 - Multi-Greenhouse IoT Core

**Goal:** Data pipeline from multiple simulated edge nodes to group dashboard.

```text
Mosquitto + Multi-Greenhouse Simulator + FastAPI + InfluxDB + NiceGUI dashboard
```

**Result:** Multiple greenhouse/zone simulators publish telemetry -> MQTT -> API -> InfluxDB -> UI shows group, greenhouse, and zone charts.

**Scope:**
- Docker Compose with Mosquitto and InfluxDB
- Simulator publishing telemetry for multiple greenhouses and zones
- MQTT topics with group_id, greenhouse_id, and zone_id
- FastAPI endpoints for latest telemetry, group summary, greenhouse summary, zone summary, and comparisons
- NiceGUI dashboard with group overview, greenhouse cards, zone detail, and live charts
- InfluxDB write/read for scoped time-series data

---

## MVP 2 - Fleet Metadata Core

**Goal:** System knows about greenhouse groups, greenhouses, zones, devices, plant batches, and optimal conditions.

```text
PostgreSQL + groups + greenhouses + zones + devices + plant_batches + plant_profiles + policies + logs
```

**Result:** System knows which greenhouses and zones exist, which plants grow where, which sensors/actuators belong to each zone, and what parameters are normal.

**Scope:**
- PostgreSQL + pgvector Docker image
- Alembic migrations for all fleet tables
- Greenhouse group CRUD
- Greenhouse and zone CRUD
- Device registry for edge nodes, sensors, and actuators
- Plant batches assigned to zones
- Plant profiles with threshold values
- Group control policies and zone setpoints
- Basic alert generation when thresholds are exceeded
- Command log and alert log recording

---

## MVP 3 - AI Chat with Group-Aware Tools

**Goal:** User can ask natural language questions about one zone, one greenhouse, or the whole group and get data-grounded answers.

```text
OpenRouter + Pydantic AI tool calling + group/greenhouse/zone read-only tools
```

**Result:** User: "How are my greenhouses?" -> AI analyzes actual group data and responds with prioritized state.

**Scope:**
- OpenRouter provider integration through the selected agent framework
- Agent loop with tool calling
- Read-only tools: get_group_overview, get_greenhouses, get_greenhouse_state, get_zone_state, get_today_group_summary, get_today_greenhouse_summary, get_today_zone_summary, compare_greenhouses, get_active_alerts
- AI conversation persistence with group/greenhouse/zone scope
- Tool call logging for explainability
- NiceGUI chat page with scope selection and tool transparency

---

## MVP 4 - RAG + Scoped Proposed Actions

**Goal:** AI has domain knowledge and can propose safe scoped actions for specific greenhouse zones.

```text
pgvector + rag_documents + search_plant_knowledge + propose_action + approve -> scoped MQTT command
```

**Result:** AI explains issues with agronomic context and proposes safe actions that the user can approve for a specific group/greenhouse/zone.

**Scope:**
- RAG document ingestion and embedding
- search_plant_knowledge tool with source attribution
- Scoped proposed action tool: propose_action(group_id, greenhouse_id, zone_id, actuator, action, duration_seconds, reason)
- Safety validation layer using zone state, greenhouse state, group policies, actuator limits, and command history
- Command approval workflow in UI
- MQTT command execution after approval using scoped topics
- Baseline control engine as observer/proposer, not autonomous publisher
