# 03. Операційні потоки системи

## Flow 1: створення структури група → теплиця → зона

```text
Оператор відкриває /zones
  -> створює або обирає GreenhouseGroup
  -> створює Greenhouse у групі
  -> створює GreenhouseZone у теплиці
  -> задає source_type: simulator або real/mqtt
  -> додає EdgeNode для теплиці
  -> додає Sensor registry для zone metrics
  -> додає Actuator registry: pump/fan/heater/lamp
  -> прив'язує PlantBatch до PlantProfile
  -> задає ControlSetpoint-и для температури, вологості ґрунту, CO2, світла
```

Навіщо це потрібно:

- MQTT topic і payload мають збігатися з реальною структурою.
- AI tools можуть коректно відповідати тільки коли знають scope.
- Safety layer може перевірити команду тільки коли знає actuator capabilities і setpoints.

## Flow 2: internal simulator demo

```text
/settings
  -> Control Mode = Internal simulator
  -> Save
/simulator
  -> scenario: normal / dry_soil / overheating / low_light
  -> topology: groups, greenhouses, zones
  -> Start Simulator
Simulator process
  -> publish telemetry every interval
FastAPI MQTTRuntime
  -> ingest telemetry
InfluxDB
  -> store microclimate points
/dashboard
  -> show group/greenhouse/zone summaries
/control
  -> propose command
  -> approve command
Simulator mode router
  -> applies state change without real MQTT device
```

Коли використовувати:

- демонстрація без ESP32;
- тестування UI й AI flows;
- перевірка group/greenhouse/zone масштабування;
- швидке створення даних для AI Chat.

## Flow 3: Wokwi / ESP32 MQTT інтеграція

```text
1. Підняти public Mosquitto broker на VPS.
2. У app .env вказати MQTT_HOST, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD.
3. У firmware/wokwi-greenhouse-zone/config.py вказати:
   - MQTT_HOST / MQTT_PORT
   - MQTT_USER / MQTT_PASSWORD
   - GROUP_ID / GREENHOUSE_ID / ZONE_ID
4. У Wokwi відкрити MicroPython project.
5. Запустити simulation.
6. Переконатися, що serial monitor показує Wi-Fi connected і MQTT connected.
7. У /settings обрати MQTT remote devices.
8. У /simulator перевірити MQTT status panel.
9. У /dashboard побачити telemetry.
10. У /control або /ai-chat створити й підтвердити команду.
11. ESP32 отримує command topic і перемикає LED актуатора.
```

Важлива умова: hosted Wokwi не бачить Docker `localhost`, тому broker має бути публічно доступним.

## Flow 4: телеметрія

```text
Device creates TelemetryEnvelope
  -> topic: greenhouse-groups/{group}/greenhouses/{greenhouse}/zones/{zone}/telemetry
  -> payload contains same group_id/greenhouse_id/zone_id
Mosquitto receives publish
FastAPI wildcard subscriber receives message
TelemetryIngestion:
  -> parse topic
  -> decode JSON
  -> validate Pydantic schema
  -> reject stale timestamp
  -> reject NaN/Inf/out-of-contract metric
  -> compare topic scope vs payload scope
  -> check message_id idempotency
  -> write InfluxDB point
```

Метрики:

- `temperature`
- `air_humidity`
- `soil_moisture`
- `co2`
- `light`
- `pump_state`
- `fan_power`
- `heater_power`
- `lamp_state`

## Flow 5: операторська команда з Control page

```text
/control
  -> operator selects group/greenhouse/zone
  -> clicks zone on greenhouse map
  -> opens actuator controls
  -> chooses actuator/action/duration/value
  -> API creates CommandLog(state=proposed)
  -> SafetyValidator validates proposal
  -> UI shows approval workflow
  -> operator approves
  -> SafetyValidator revalidates current state
  -> if mode=simulator: simulator mode router applies command
  -> if mode=mqtt: CommandPublisher publishes MQTT command
```

Чому потрібна повторна валідація:

- telemetry могла змінитися між propose і approve;
- cooldown міг активуватися;
- інша команда могла вже змінити стан актуатора;
- group policy могла стати stricter.

## Flow 6: AI chat scoped analysis

```text
/ai-chat
  -> user selects conversation or creates new conversation
  -> user selects scope: group / greenhouse / zone
  -> user asks natural language question
FastAPI /api/ai/chat
  -> loads conversation history bounded window
  -> creates AIScope
  -> sends prompt to Pydantic AI Agent
Agent
  -> calls read-only tools
  -> may call RAG search
  -> returns structured response
UI
  -> renders summary, observations, recommendations
  -> renders tool-call trace
  -> renders proposed action cards if present
```

AI може:

- пояснити проблему;
- порівняти теплиці;
- знайти зони з ризиком;
- використати RAG knowledge;
- запропонувати полив/вентиляцію/освітлення/нагрів.

AI не може:

- напряму publish MQTT;
- приховувати tool calls;
- вигадувати telemetry;
- створювати фізичну дію без `group_id`, `greenhouse_id`, `zone_id`.

## Flow 7: RAG knowledge base

```text
/rag
  -> admin adds document: plant care, system constraints, local notes
API
  -> stores rag_document
Worker/API
  -> chunks document
  -> creates embeddings
  -> stores rag_chunks with pgvector embedding
AI Chat
  -> calls search_plant_knowledge(query, group_id)
  -> receives cited chunks
  -> combines RAG + telemetry + plant profile + alerts
```

Типи корисних RAG-документів:

- догляд за томатами/огірками/салатом/перцем;
- дефіцит води, перегрів, симптоми стресу;
- CO2 interpretation;
- локальні правила господарства;
- обмеження актуаторів і обладнання;
- нотатки оператора для конкретної групи.

## Flow 8: control engine observer/proposer

```text
Control engine one-shot або background job
  -> reads zones + setpoints + latest telemetry
  -> evaluate_zone_rules
  -> creates ControlProposal list
  -> CommandService.propose
  -> SafetyValidator validates
  -> UI shows proposals
  -> user approves/rejects
```

Поточна роль control engine — **observer/proposer**, не autonomous publisher. Це важливо для безпеки: навіть rule-based automation має проходити через той самий CommandLog і approval pipeline.

## Flow 9: alerts and logs

```text
Telemetry or rule evaluation
  -> threshold exceeded
  -> Alert created or updated
UI alert panel
  -> shows active alerts
AI tools
  -> get_active_alerts(scope)
Logs page
  -> debug_log entries
  -> ai_tool_calls correlation
```

Рекомендована майбутня модель alert lifecycle:

```text
active -> acknowledged -> resolved
active -> dismissed
active -> escalated -> resolved
```

## Flow 10: production verification

Production перевіряти через deployed domain/nginx, не тільки через localhost або internal Docker.

```text
Browser -> HTTPS deployed domain -> nginx -> app container
External Wokwi/ESP32 -> public MQTT TLS -> mosquitto -> app MQTT runtime
App -> PostgreSQL/InfluxDB/OpenRouter
```

Мінімальні production checks:

- deployed domain відкриває UI;
- admin auth працює;
- dashboard завантажується;
- AI chat повертає відповідь або зрозумілу помилку;
- MQTT status показує broker connection;
- Wokwi telemetry доходить до app;
- approved command доходить до Wokwi;
- logs не містять `ai_chat_failed` або ingestion errors після тесту.
