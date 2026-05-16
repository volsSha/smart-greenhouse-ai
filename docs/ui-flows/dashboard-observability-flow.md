# Dashboard and Observability Flow

Dashboard, logs, and RAG pages provide visibility into greenhouse state and AI/control behavior.

## Dashboard Load Flow

```text
Open /dashboard
  -> GET /api/groups
  -> choose first group with telemetry when available
  -> GET /api/groups/{group_id}/telemetry/latest
  -> GET /api/groups/{group_id}/telemetry/anomalies
  -> render group overview, greenhouse cards, zone status, and alerts
```

## Greenhouse Drill-Down Flow

```text
User clicks View zones on greenhouse card
  -> expand greenhouse details
  -> render zone detail cards
  -> GET /api/groups/{group_id}/telemetry/range with greenhouse/zone filters
  -> render 6-hour charts
     -> temperature
     -> humidity
     -> soil moisture
     -> multi-metric trend
```

## Telemetry Source Flow

```text
Internal simulator OR MQTT edge node
  -> publish telemetry with group/greenhouse/zone IDs
  -> backend validates and stores time-series data
  -> /dashboard reads latest and historical telemetry
  -> /control reads latest zone telemetry
  -> /ai-chat tools analyze the same scoped data
```

## Logs Flow

```text
Open /logs
  -> GET /api/debug-logs
  -> user filters by level/component/event_type
     -> GET /api/debug-logs with query params
  -> user expands log entry
     -> view metadata, request_id, duration, error_type, and stack trace
```

Use `/logs` first when investigating API, UI, or AI command failures. AI chat failures are persisted with `component="ai_agent"` and `event_type="ai_chat_failed"`.

## RAG Flow

```text
Open /rag
  -> GET /api/rag/documents
  -> Add Document
     -> POST /api/rag/documents
     -> backend chunks and embeds content
  -> Upload text file
     -> file content fills document form
  -> Reindex All Documents
     -> POST /api/rag/reindex
  -> Search
     -> GET /api/rag/search
     -> ranked chunks render with source and score
```

## Related Files

- `app/ui/pages/dashboard.py`
- `app/ui/pages/logs.py`
- `app/ui/pages/rag.py`
- `app/ui/components/telemetry_cards.py`
- `app/ui/components/telemetry_charts.py`
- `app/ui/components/alert_panel.py`
- `app/api/telemetry.py`
- `app/api/debug_logs.py`
- `app/api/rag.py`