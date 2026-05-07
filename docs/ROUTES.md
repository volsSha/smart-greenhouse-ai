# API Routes

## Telemetry

| Method | Endpoint                     | Description                  |
|--------|------------------------------|------------------------------|
| GET    | `/api/telemetry/latest`      | Latest sensor readings       |
| GET    | `/api/telemetry/summary/today` | Today's aggregated summary  |
| GET    | `/api/telemetry/range`       | Historical telemetry range   |
| GET    | `/api/telemetry/anomalies`   | Detected anomalies           |

## Plants

| Method | Endpoint               | Description                    |
|--------|------------------------|--------------------------------|
| GET    | `/api/plants`          | List all plants                |
| POST   | `/api/plants`          | Create plant                   |
| GET    | `/api/plants/{id}`     | Get plant details              |
| PATCH  | `/api/plants/{id}`     | Update plant                   |

## AI Chat

| Method | Endpoint                        | Description                       |
|--------|---------------------------------|-----------------------------------|
| POST   | `/api/ai/chat`                  | Send message to AI agent          |
| GET    | `/api/ai/conversations`         | List conversations                |
| GET    | `/api/ai/conversations/{id}`    | Get conversation with messages    |
| GET    | `/api/ai/tool-calls/{conv_id}`  | Get tool calls for conversation   |

## Commands

| Method | Endpoint                         | Description                        |
|--------|----------------------------------|------------------------------------|
| POST   | `/api/commands/propose`          | Propose a control command          |
| POST   | `/api/commands/{id}/approve`     | Approve proposed command           |
| POST   | `/api/commands/{id}/cancel`      | Cancel proposed command            |
| GET    | `/api/commands/recent`           | Recent command history             |

## RAG

| Method | Endpoint              | Description                     |
|--------|-----------------------|---------------------------------|
| POST   | `/api/rag/documents`  | Add document to knowledge base  |
| POST   | `/api/rag/reindex`    | Rebuild embeddings              |
| GET    | `/api/rag/search`     | Semantic search in knowledge    |

## NiceGUI Pages

| Page          | Description                                     |
|---------------|-------------------------------------------------|
| `/dashboard`  | Current metrics, actuator state, alerts, AI summary |
| `/simulator`  | Sensor emulation with sliders and scenario buttons  |
| `/plants`     | Plant management, profiles, growth stages        |
| `/control`    | Manual control, setpoints, control modes         |
| `/ai-chat`    | AI conversation with tool call transparency      |
| `/logs`       | Command log, event log, alert history            |
| `/rag`        | Knowledge base management                        |
| `/settings`   | System configuration                             |

## MQTT Topics

### Telemetry

```
greenhouse/{id}/telemetry
greenhouse/{id}/telemetry/temperature
greenhouse/{id}/telemetry/humidity
greenhouse/{id}/telemetry/soil_moisture
greenhouse/{id}/telemetry/co2
greenhouse/{id}/telemetry/light
```

### Commands

```
greenhouse/{id}/commands/pump
greenhouse/{id}/commands/fan
greenhouse/{id}/commands/heater
greenhouse/{id}/commands/lamp
```

### Events

```
greenhouse/{id}/events
greenhouse/{id}/alerts
greenhouse/{id}/actuators/state
```
