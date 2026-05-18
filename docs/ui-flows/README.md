# UI Flow Documentation

This directory documents the implemented Smart Greenhouse UI flows in arrow-style steps and diagrams. Use this file as the orchestrator when you need to understand how pages, buttons, APIs, and backend logic connect.

## Flow Map

```text
User opens app
  -> / redirects to /dashboard
  -> sidebar navigation
     -> Operations
        -> /dashboard: fleet telemetry overview and greenhouse drill-down
        -> /simulator: internal simulator runtime and live zone visualization
        -> /zones: group, greenhouse, zone, edge-node, and plant-batch setup
        -> /plants: planned plant-profile and plant-batch workspace
        -> /control: operator control panel and command approval workflow
     -> Intelligence
        -> /ai-chat: scoped AI analysis and proposed actions
        -> /rag: knowledge-base documents and semantic search
        -> /logs: persisted debug and failure investigation
     -> System
        -> /settings: model catalog, selected AI model, and control mode
```

## Documents

- [Navigation and page inventory](navigation.md) — sidebar structure, pages, primary buttons, and API dependencies.
- [Simulator flow](simulator-flow.md) — starting/stopping the internal simulator, MQTT-mode guard rails, and live visualization polling.
- [Control panel flow](control-panel-flow.md) — group/greenhouse/zone selection, map interactions, actuator proposals, and approvals.
- [AI chat flow](ai-chat-flow.md) — conversation scope, tool traces, response rendering, and proposed action cards.
- [Settings and control mode flow](settings-control-mode-flow.md) — how MQTT vs simulator mode propagates through Settings, Simulator, Control, and Commands.
- [Zone and plant setup flow](zone-plant-setup-flow.md) — registry setup, zone creation, edge-node identity, MQTT topics, and plant batches.
- [Dashboard and observability flow](dashboard-observability-flow.md) — telemetry overview, drill-down charts, logs, and RAG support flows.

## Cross-Page Logic Diagram

```text
/settings
  -> Save Control Mode
     -> PUT /api/settings/control-mode
        -> persisted settings.control_mode
           -> /simulator reads mode and blocks internal simulator when mode = mqtt
           -> /control reads mode and checks simulator status when mode = simulator
           -> /api/commands/propose normalizes command mode
              -> user approval
                 -> /api/commands/{id}/approve
                    -> simulator mode router OR MQTT command publisher
```

## Main User Journeys

### Internal simulation demo

```text
Open /settings
  -> choose Internal simulator
  -> Save Control Mode
  -> open /simulator
  -> choose scenario and topology counts
  -> Start Simulator
  -> live zones poll every 2 seconds
  -> open /dashboard
  -> inspect latest telemetry and charts
  -> open /control
  -> select group and greenhouse
  -> click zone
  -> propose actuator command
  -> approve command
  -> simulator mode router applies zone state change
```

### Real MQTT / Wokwi device flow

```text
Open /zones
  -> select group
  -> select greenhouse
  -> Add zone
  -> edge node credentials and telemetry topic are available
  -> copy topic/config into Wokwi firmware
  -> open /settings
  -> choose MQTT remote devices
  -> Save Control Mode
  -> open /simulator
  -> MQTT status panel shows broker status
  -> Wokwi device publishes telemetry
  -> dashboard/control/AI chat read scoped telemetry
  -> approved command publishes to scoped MQTT command topic
```

### AI-assisted control flow

```text
Open /ai-chat
  -> select group / greenhouse / zone scope, or keep fleet-wide
  -> send question
  -> AI calls read-only telemetry/RAG/tools
  -> response shows observations, recommendations, and tool traces
  -> AI may create a proposed action
  -> proposed action card appears in chat
  -> operator approves or rejects
  -> backend safety validation runs again before execution
```

## Related Reference Docs

- `docs/ARCHITECTURE.md` — domain model, MQTT topic model, safety layer, and sensor-to-AI data flow.
- `docs/ROUTES.md` — HTTP endpoints, NiceGUI pages, and MQTT topics.
- `docs/AI_AGENT.md` — AI tool model, proposed action rules, and response shape.
- `docs/wokwi-mqtt-mode.md` — Wokwi/MQTT setup and verification.
- `firmware/wokwi-greenhouse-zone/README.md` — firmware configuration and device-side setup.
- `docs/OPERATIONS.md` — local services and manual verification checklist.
