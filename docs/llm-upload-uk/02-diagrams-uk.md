# 02. UML/Mermaid діаграми українською

Цей файл містить діаграми у Mermaid syntax. Їх можна вставляти в Mermaid Live Editor, GitHub Markdown або передавати LLM/генератору зображень як структурний опис.

## 1. Компонентна діаграма системи

```mermaid
flowchart LR
    subgraph UI[Операторський інтерфейс NiceGUI]
        DASH[Dashboard]
        ZONES[Zones]
        CONTROL[Control]
        SIM[Simulator]
        CHAT[AI Chat]
        RAGUI[RAG]
        LOGS[Logs]
        SETTINGS[Settings]
    end

    subgraph API[FastAPI backend]
        REST[REST routers]
        MQTT_RT[MQTT runtime subscriber]
        INGEST[Telemetry ingestion]
        CMD[Command service]
        SAFETY[Safety validator]
        AI[Greenhouse AI Agent]
        RAG[RAG service]
    end

    subgraph DATA[Сховища]
        PG[(PostgreSQL + pgvector)]
        INFLUX[(InfluxDB)]
    end

    subgraph MQTT[Mosquitto MQTT broker]
        BROKER[Scoped telemetry/commands topics]
    end

    subgraph EDGE[Edge nodes]
        WOKWI[Wokwi ESP32 MicroPython]
        REAL[Реальний ESP32]
        INTERNAL[Internal Python simulator]
    end

    UI -->|HTTP/WebSocket| API
    WOKWI -->|telemetry| BROKER
    REAL -->|telemetry| BROKER
    INTERNAL -->|telemetry| BROKER
    BROKER --> MQTT_RT
    MQTT_RT --> INGEST
    INGEST --> INFLUX
    REST --> PG
    AI --> PG
    AI --> INFLUX
    AI --> RAG
    RAG --> PG
    CONTROL -->|propose/approve| REST
    CHAT -->|question + scope| REST
    CMD --> SAFETY
    SAFETY --> PG
    CMD -->|approved command| BROKER
    BROKER -->|commands| WOKWI
    BROKER -->|commands| REAL
    BROKER -->|commands| INTERNAL
```

## 2. Доменна модель / class diagram

```mermaid
classDiagram
    class GreenhouseGroup {
        +id
        +name
        +description
    }
    class Greenhouse {
        +id
        +group_id
        +name
        +location
    }
    class GreenhouseZone {
        +id
        +greenhouse_id
        +name
        +source_type
        +simulator_managed
    }
    class EdgeNode {
        +id
        +greenhouse_id
        +node_type
        +mqtt_client_id
    }
    class Sensor {
        +id
        +zone_id
        +sensor_key
        +metric
    }
    class Actuator {
        +id
        +zone_id
        +actuator_type
        +capabilities
    }
    class PlantProfile {
        +id
        +crop_name
        +growth_stage
        +thresholds
    }
    class PlantBatch {
        +id
        +zone_id
        +profile_id
        +planted_at
    }
    class ControlSetpoint {
        +id
        +zone_id
        +metric
        +min_value
        +max_value
    }
    class GroupControlPolicy {
        +id
        +group_id
        +policy JSONB
    }
    class Alert {
        +id
        +scope
        +severity
        +status
    }
    class CommandLog {
        +id
        +scope
        +actuator
        +action
        +state
        +source
    }
    class AIConversation {
        +id
        +scope
        +title
    }
    class AIMessage {
        +id
        +conversation_id
        +role
        +content
    }
    class AIToolCall {
        +id
        +message_id
        +tool_name
        +arguments
        +result
    }
    class RAGDocument {
        +id
        +group_id
        +title
        +source
    }
    class RAGChunk {
        +id
        +document_id
        +content
        +embedding
    }

    GreenhouseGroup "1" --> "many" Greenhouse
    Greenhouse "1" --> "many" GreenhouseZone
    Greenhouse "1" --> "0..*" EdgeNode
    GreenhouseZone "1" --> "many" Sensor
    GreenhouseZone "1" --> "many" Actuator
    GreenhouseZone "1" --> "many" PlantBatch
    PlantProfile "1" --> "many" PlantBatch
    GreenhouseZone "1" --> "many" ControlSetpoint
    GreenhouseGroup "1" --> "many" GroupControlPolicy
    GreenhouseZone "1" --> "many" Alert
    GreenhouseZone "1" --> "many" CommandLog
    AIConversation "1" --> "many" AIMessage
    AIMessage "1" --> "many" AIToolCall
    GreenhouseGroup "1" --> "many" RAGDocument
    RAGDocument "1" --> "many" RAGChunk
```

## 3. Use case diagram

```mermaid
flowchart TB
    OP[Оператор]
    ADMIN[Адміністратор]
    AIUSER[Користувач AI Chat]
    DEVICE[ESP32/Wokwi пристрій]

    subgraph UC[Варіанти використання]
        UC1[Переглянути стан групи теплиць]
        UC2[Налаштувати групи, теплиці, зони]
        UC3[Зареєструвати edge-node, сенсори, актуатори]
        UC4[Запустити internal simulator]
        UC5[Підключити Wokwi/ESP32 через MQTT]
        UC6[Отримати телеметрію]
        UC7[Поставити питання AI]
        UC8[AI викликає read-only tools]
        UC9[AI створює proposed action]
        UC10[Підтвердити або відхилити команду]
        UC11[Перевірити logs/tool traces]
        UC12[Додати RAG-документ]
        UC13[Змінити AI model/control mode]
    end

    OP --> UC1
    OP --> UC4
    OP --> UC10
    OP --> UC11
    ADMIN --> UC2
    ADMIN --> UC3
    ADMIN --> UC12
    ADMIN --> UC13
    AIUSER --> UC7
    UC7 --> UC8
    UC8 --> UC9
    UC9 --> UC10
    DEVICE --> UC5
    DEVICE --> UC6
```

## 4. Sequence: телеметрія від ESP32 до dashboard/AI

```mermaid
sequenceDiagram
    participant ESP as ESP32/Wokwi
    participant MQTT as Mosquitto MQTT
    participant RT as FastAPI MQTT Runtime
    participant ING as TelemetryIngestion
    participant INF as InfluxDB
    participant UI as NiceGUI Dashboard
    participant AI as AI Agent Tool

    ESP->>MQTT: publish telemetry topic
    MQTT->>RT: subscribed wildcard receives message
    RT->>ING: raw topic + JSON payload
    ING->>ING: parse topic scope
    ING->>ING: validate TelemetryEnvelope
    ING->>ING: check group/greenhouse/zone IDs
    ING->>ING: check message_id idempotency
    ING->>INF: write microclimate point
    UI->>INF: read latest/summary telemetry
    AI->>INF: get_today_zone_summary / group summary
```

## 5. Sequence: AI пропонує полив, оператор підтверджує

```mermaid
sequenceDiagram
    participant User as Оператор
    participant Chat as NiceGUI AI Chat
    participant API as FastAPI /api/ai/chat
    participant Agent as Pydantic AI Agent
    participant Tools as Read-only tools
    participant DB as PostgreSQL/InfluxDB/RAG
    participant Cmd as CommandService
    participant Safety as SafetyValidator
    participant MQTT as Mosquitto
    participant ESP as ESP32/Wokwi

    User->>Chat: Запит "Чи треба полити zone-01?"
    Chat->>API: message + AIScope
    API->>Agent: chat(conversation_id, scope, message)
    Agent->>Tools: get_zone_state
    Tools->>DB: read metadata + telemetry
    DB-->>Tools: current zone data
    Tools-->>Agent: tool result
    Agent->>Tools: search_plant_knowledge
    Tools->>DB: pgvector search
    DB-->>Tools: cited knowledge chunks
    Tools-->>Agent: RAG result
    Agent-->>API: structured response + proposed_action
    API->>Cmd: store proposed command
    Cmd->>Safety: validate proposal
    Safety-->>Cmd: valid or rejected
    API-->>Chat: response + approval card
    User->>Chat: Approve
    Chat->>Cmd: approve command
    Cmd->>Safety: revalidate current state
    Safety-->>Cmd: ok
    Cmd->>MQTT: publish command QoS 1
    MQTT->>ESP: command topic
    ESP->>ESP: apply actuator LED/state
```

## 6. State diagram: життєвий цикл команди

```mermaid
stateDiagram-v2
    [*] --> proposed
    proposed --> validated: safety ok
    proposed --> rejected: safety failed
    validated --> approved: user confirms
    validated --> expired: timeout
    approved --> executing: execute=true
    approved --> cancelled: user cancels before execution
    executing --> executed: MQTT publish success / simulator applied
    executing --> failed: publish/apply error
    rejected --> [*]
    expired --> [*]
    cancelled --> [*]
    executed --> [*]
    failed --> [*]
```

## 7. Activity: internal simulator demo

```mermaid
flowchart TD
    A[Відкрити /settings] --> B[Обрати Internal simulator]
    B --> C[Зберегти control mode]
    C --> D[Відкрити /simulator]
    D --> E[Обрати topology counts + scenario]
    E --> F[Start Simulator]
    F --> G[Simulator publishes MQTT telemetry]
    G --> H[Dashboard показує live cards/charts]
    H --> I[Відкрити /control]
    I --> J[Обрати group/greenhouse/zone]
    J --> K[Запропонувати команду]
    K --> L[Підтвердити]
    L --> M[Simulator mode router updates zone state]
```

## 8. Activity: Wokwi/ESP32 MQTT flow

```mermaid
flowchart TD
    A[Створити group/greenhouse/zone у /zones] --> B[Зареєструвати edge-node]
    B --> C[Скопіювати group_id greenhouse_id zone_id]
    C --> D[Налаштувати firmware/wokwi-greenhouse-zone/config.py]
    D --> E[Вказати public MQTT broker]
    E --> F[Запустити hosted Wokwi]
    F --> G[ESP32 підключається до Wi-Fi Wokwi-GUEST]
    G --> H[ESP32 підключається до Mosquitto]
    H --> I[ESP32 publish telemetry]
    I --> J[FastAPI MQTT runtime ingest]
    J --> K[Dashboard/Control/AI бачать дані]
    K --> L[Оператор approve command]
    L --> M[MQTT command topic]
    M --> N[ESP32 змінює LED актуатора]
```

## 9. Deployment diagram

```mermaid
flowchart TB
    subgraph Browser[Клієнтський браузер]
        BROWSER[NiceGUI pages]
    end

    subgraph VPS[VPS / Docker host]
        NGINX[Nginx reverse proxy]
        APP[app container: FastAPI + NiceGUI + MQTT runtime]
        MOSQ[mosquitto container]
        PG[(postgres + pgvector volume)]
        INF[(influxdb volume)]
    end

    subgraph External[Зовнішні сервіси]
        OPENROUTER[OpenRouter API]
        WOKWI[Hosted Wokwi]
        ESP[Real ESP32 devices]
    end

    BROWSER -->|HTTPS deployed domain| NGINX
    NGINX --> APP
    APP --> PG
    APP --> INF
    APP --> MOSQ
    APP -->|LLM/embeddings| OPENROUTER
    WOKWI -->|MQTT TLS 8883| MOSQ
    ESP -->|MQTT TLS 8883| MOSQ
    MOSQ -->|commands| WOKWI
    MOSQ -->|commands| ESP
```

## 10. Suggested target architecture extension: command acknowledgement

```mermaid
sequenceDiagram
    participant App as FastAPI CommandService
    participant MQTT as Mosquitto
    participant ESP as ESP32
    participant DB as PostgreSQL CommandLog

    App->>MQTT: publish command_id on commands topic
    App->>DB: state = executed_published
    MQTT->>ESP: deliver command
    ESP->>ESP: validate target identity and actuator
    ESP->>ESP: apply command
    ESP->>MQTT: publish state/ack {command_id, result, actuator_state}
    MQTT->>App: state/ack subscriber receives message
    App->>DB: state = device_confirmed or device_failed
```
