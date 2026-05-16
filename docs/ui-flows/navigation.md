# Navigation and Page Inventory

The NiceGUI shell is registered in `app/ui/layouts/main_layout.py`. Page modules register routes with `@ui.page(...)` and are imported before `ui.run_with(...)` starts the UI.

## Sidebar Structure

```text
/
  -> redirect to /dashboard

Sidebar
  -> Operations
     -> Dashboard (/dashboard)
     -> Simulator (/simulator)
     -> Zones (/zones)
     -> Plants (/plants)
     -> Control (/control)
  -> Intelligence
     -> AI Chat (/ai-chat)
     -> RAG (/rag)
     -> Logs (/logs)
  -> System
     -> Settings (/settings)
```

## Page Inventory

| Page | Source | Primary purpose |
|---|---|---|
| `/dashboard` | `app/ui/pages/dashboard.py` | Fleet telemetry overview, greenhouse cards, anomalies, and chart drill-downs. |
| `/simulator` | `app/ui/pages/simulator.py` | Start/stop internal simulator, choose scenarios, view live zone state, inspect MQTT status. |
| `/zones` | `app/ui/pages/zone_management.py` | Create zones, edge nodes, plant batches, and copy MQTT topics for firmware. |
| `/plants` | `app/ui/pages/plants.py` | Planned plant-profile and plant-batch workspace. |
| `/control` | `app/ui/pages/control.py` | Operator panel for zone selection, actuator proposals, and command approval. |
| `/ai-chat` | `app/ui/pages/ai_chat.py` | Scoped AI conversation with tool traces and proposed action cards. |
| `/rag` | `app/ui/pages/rag.py` | Knowledge-base document creation, upload, reindex, and semantic search. |
| `/logs` | `app/ui/pages/logs.py` | Debug log filtering and failure investigation. |
| `/settings` | `app/ui/pages/settings.py` | OpenRouter model catalog, selected model, embedding settings, and control mode. |

## Header Flow

```text
Any page render
  -> main layout wraps content
  -> header displays app title
  -> language switcher renders current locale label
  -> user changes language
     -> app.storage.user locale updates
     -> page refreshes with translated labels
```

## Common UI Patterns

```text
Page enters
  -> render page hero
  -> load data through app/ui/api_client.py
  -> show cards/selectors/buttons
  -> user action calls FastAPI endpoint
  -> component refreshes affected section
```

Selectors usually cascade from larger scope to smaller scope:

```text
Group selected
  -> load greenhouses for group
  -> greenhouse selected
     -> load zones / plant batches / telemetry for greenhouse
        -> zone selected
           -> render zone-specific controls or context
```