# Tech Stack

## Core Stack

| Layer         | Technology                | Purpose                                                      |
|---------------|---------------------------|--------------------------------------------------------------|
| UI            | **NiceGUI**               | Web interface, dashboard, chat, sensor emulator              |
| Backend API   | **FastAPI**               | REST, WebSocket, tool endpoints, safety layer                |
| MQTT broker   | **Mosquitto**             | Telemetry and command exchange                               |
| Time-series   | **InfluxDB**              | Temperature, humidity, CO2, light, soil moisture             |
| Relational DB | **PostgreSQL**            | Users, greenhouses, plants, settings, commands, AI logs      |
| Vector search | **pgvector**              | RAG for plant knowledge, care rules, documentation           |
| LLM provider  | **OpenRouter**            | LLM, tool calling, agent workflow                            |
| Control       | **Python PID/Fuzzy**      | Automatic control (simple-pid, scikit-fuzzy)                 |
| Containers    | **Docker Compose**        | Single repository, single startup                            |

## Component Roles

| Component         | Role                                                                 |
|-------------------|----------------------------------------------------------------------|
| NiceGUI           | Human-machine interface                                              |
| FastAPI           | Central logic, API, tools, safety validation                         |
| Mosquitto         | Telemetry/command transport                                          |
| InfluxDB          | Sensor time-series                                                   |
| PostgreSQL        | System structure, plants, users, commands, logs                      |
| pgvector          | RAG memory for agronomic knowledge                                   |
| OpenRouter        | LLM reasoning, tool calling, explanations, proposed actions          |
| Control Engine    | Autonomous PID/Fuzzy loop                                            |
| Simulator         | Virtual ESP32                                                        |

## Python Dependencies

### Base

```
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
simple-pid
scikit-fuzzy
python-dotenv
httpx
openrouter
pytest
pytest-asyncio
```

### AI / RAG

```
tiktoken
sentence-transformers
```

## Infrastructure Images

| Service       | Image                          | Port  |
|---------------|--------------------------------|-------|
| Mosquitto     | eclipse-mosquitto:2            | 1883, 9001 |
| PostgreSQL    | pgvector/pgvector:pg16         | 5432  |
| InfluxDB      | influxdb:2.7                   | 8086  |
| Grafana       | grafana/grafana                | 3000  |
