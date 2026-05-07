# MVP Roadmap

## MVP 1 - IoT Core

**Goal:** Data pipeline from simulated sensors to dashboard.

```
Mosquitto + Simulator + FastAPI + InfluxDB + NiceGUI dashboard
```

**Result:** Sensors are simulated -> MQTT -> API -> InfluxDB -> UI shows charts.

**Scope:**
- Docker Compose with Mosquitto and InfluxDB
- Sensor simulator publishing telemetry via MQTT
- FastAPI endpoints for latest telemetry and today's summary
- NiceGUI dashboard with live charts
- InfluxDB write/read for time-series data

---

## MVP 2 - PostgreSQL Core

**Goal:** System knows about plants and their optimal conditions.

```
PostgreSQL + plants + greenhouses + plant_profiles + command_log + alert_log
```

**Result:** System knows which plants grow in the greenhouse and what parameters are normal for them.

**Scope:**
- PostgreSQL + pgvector Docker image
- Alembic migrations for all tables
- Plant CRUD API
- Plant profiles with threshold values
- Basic alert generation when thresholds are exceeded
- Command log recording

---

## MVP 3 - AI Chat with Tools

**Goal:** User can ask natural language questions and get data-grounded answers.

```
OpenRouter + tool calling + read-only tools
```

**Result:** User: "How are my plants?" -> AI analyzes actual data and responds.

**Scope:**
- OpenRouter client integration
- Agent loop with tool calling
- Read-only tools: get_plants, get_today_telemetry_summary, get_active_alerts
- AI conversation persistence (PostgreSQL)
- Tool call logging for explainability
- NiceGUI chat page with tool transparency

---

## MVP 4 - RAG + Proposed Actions

**Goal:** AI has domain knowledge and can propose safe actions.

```
pgvector + rag_documents + search_plant_knowledge + propose_watering + approve -> MQTT
```

**Result:** AI not only explains but also proposes safe actions that user can approve.

**Scope:**
- RAG document ingestion and embedding
- search_plant_knowledge tool
- Intent tools (propose_watering, propose_ventilation, etc.)
- Safety validation layer
- Command approval workflow in UI
- MQTT command execution after approval
