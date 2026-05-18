# Settings and Control Mode Flow

The settings page is implemented in `app/ui/pages/settings.py`. It manages the selected OpenRouter chat model and the persisted control mode used by simulator, control, and command execution flows.

## Settings Page Load Flow

```text
Open /settings
  -> GET /api/settings
     -> render selected chat model
     -> render fixed embedding configuration
     -> render current control_mode
  -> GET /api/settings/catalog
     -> render searchable/filterable model catalog table
```

## Model Catalog Flow

```text
User searches or filters catalog
  -> GET /api/settings/catalog?search=...&provider=...&capability=...
  -> AG Grid updates model rows

User clicks Refresh Catalog
  -> POST /api/settings/catalog/refresh
  -> backend fetches OpenRouter catalog
  -> page reloads catalog rows

User selects model row
  -> Use Selected Model
     -> PUT /api/settings
     -> selected_chat_model persists
     -> future /api/ai/chat calls use selected model
```

## Control Mode Save Flow

```text
User selects control mode
  -> MQTT remote devices OR Internal simulator
  -> Save Control Mode
     -> PUT /api/settings/control-mode
        -> persisted control_mode updates
        -> when switching to mqtt, backend stops internal simulator
     -> settings page refreshes current mode
```

## Cross-Page Propagation

```text
/settings saves control_mode
  -> /simulator
     -> GET /api/settings
     -> blocks Start Simulator when control_mode = mqtt
     -> shows MQTT status panel for Wokwi/MQTT operation
  -> /control
     -> GET /api/settings
     -> if simulator mode, require running simulator before proposals
     -> include mode in proposed commands
  -> /api/commands/propose
     -> normalizes command mode against persisted control_mode
  -> /api/commands/{id}/approve
     -> simulator mode executes through simulator mode router
     -> mqtt mode publishes to scoped MQTT command topic
```

## Mode Decision Diagram

```text
Need to test without hardware?
  -> choose Internal simulator in /settings
  -> run /simulator
  -> use /control or /ai-chat to create proposals

Need Wokwi or physical edge nodes?
  -> create zones and edge nodes in /zones
  -> configure firmware topic and broker
  -> choose MQTT remote devices in /settings
  -> observe telemetry in /dashboard and /control
  -> approved commands publish to MQTT
```

## Related Files

- `app/ui/pages/settings.py`
- `app/api/settings.py`
- `app/ui/pages/simulator.py`
- `app/ui/pages/control.py`
- `app/api/commands.py`
- `app/services/simulator/mode_router.py`