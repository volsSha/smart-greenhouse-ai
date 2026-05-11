---
title: "feat: Simulator Mode with AI-Driven Animated Visual Feedback"
type: feat
status: active
date: 2026-05-11
---

# Simulator Mode with AI-Driven Animated Visual Feedback

## Summary

Add an interactive zone visualization to the simulator page that shows animated visual feedback when AI-proposed actions (watering, ventilation, lighting, heating) are applied. When a user approves a proposed action from the AI chat, the simulator internally updates simulated zone state and the visualization reflects the change with CSS animations and real-time metric updates via NiceGUI's `ui.timer()`.

---

## Problem Frame

The simulator page is currently a static control panel with no zone visualization. AI chat proposes actions (watering, ventilation, etc.) but approving them has no visible effect — commands are logged but the simulated telemetry remains unchanged. There is no SimulatedZoneState model, no real-time push mechanism to the UI, and no concept of operational modes. This plan closes the feedback loop for simulator mode: action → state change → animated visual response.

---

## Requirements

- R1. The simulator page must display an interactive visualization of greenhouse zones showing metric values (temperature, humidity, soil_moisture, co2, light) and actuator states (pump, fan, heater, lamp)
- R2. When a user approves a proposed action from the AI chat (or control page), the simulator must apply the action to an in-memory SimulatedZoneState model that influences future telemetry generation
- R3. The zone visualization must show animated visual feedback for each action type: water flow animation for pump, fan rotation for ventilation, glow for heater, light toggle for lamp
- R4. Metric values in the zone visualization must update in near-real-time (1-3 second polling interval) reflecting simulated zone state changes
- R5. A mode selector must allow switching between Internal Simulator and Wokwi/MQTT mode; only Internal Simulator mode is in scope for this plan
- R6. The AI chat proposed_action_card must support in-place approval/rejection, triggering the action execution pipeline

---

## Scope Boundaries

- Wokwi/MQTT mode implementation is in Plan 2 — not this plan
- 3D or canvas-based rendering is out of scope; CSS/SVG animations within NiceGUI are sufficient
- Modifying the AI agent's tool interface or adding new tool types is out of scope
- Real MQTT device communication stays out of scope (Plan 2)
- Production-grade IoT device management (provisioning, OTA) is out of scope
- Mobile/responsive layout changes are out of scope

### Deferred to Follow-Up Work

- Dashboard page live-refresh (currently one-shot load) — separate from simulator visualization
- Chart animations for historical telemetry on the dashboard

---

## Context & Research

### Relevant Code and Patterns

- `app/api/simulator.py` — Simulator API with `_metric_value()` pure function and `SimulatorBackgroundTask`; needs state-aware refactoring
- `app/ui/pages/simulator.py` — Current simulator page (control panel only, no zone visualization)
- `app/ui/pages/dashboard.py` — Dashboard with zone card layout and ECharts; pattern to follow for zone display
- `app/ui/components/telemetry_cards.py` — Metric badge cards with color-coded thresholds
- `app/ui/components/telemetry_charts.py` — ECharts line charts for telemetry
- `app/ui/components/proposed_action_card.py` — Already supports `on_approve`/`on_reject` callbacks
- `app/ui/pages/ai_chat.py` — AI chat page; currently renders `proposed_action_card` without approval callbacks
- `app/ui/pages/control.py` — Control page with working approval flow via POST `/api/commands/{id}/approve`
- `app/services/ai_agent/tools/proposed_action_tools.py` — Creates CommandLog entries with status `proposed` → `validated`
- `app/services/command_service.py` — `CommandService.propose()`, `approve()`, `execute()` lifecycle
- `app/services/safety_validator.py` — Validates proposed commands against safety limits
- `app/models/command.py` — `CommandLog` model with status state machine
- `app/core/safety_limits.py` — `VALID_METRICS` and safety thresholds

### Institutional Learnings

- NiceGUI must be mounted via `ui.run_with(app)` and started with `uvicorn`; never use `ui.run(app=...)`
- Docker deployment must mount all runtime asset directories (e.g., `locales/`); new static asset directories for animations must follow this pattern
- NiceGUI `ui.sidebar()` was removed; use `ui.left_drawer()` instead

### External References

- NiceGUI `ui.timer()` for periodic polling (native support, async callbacks)
- NiceGUI `ui.html()` for embedding animated SVG content
- NiceGUI `ui.add_css()` for keyframe animations (global or per-client)
- NiceGUI `ui.run_javascript()` for client-side DOM manipulation
- NiceGUI ECharts `run_chart_method()` for incremental chart updates

---

## Key Technical Decisions

- **SimulatedZoneState as in-memory service**: Create a mutable state model that the background simulator task reads and the command execution pipeline mutates. This closes the feedback loop — telemetry generation consults zone state instead of computing deterministic values
- **ui.timer() polling for real-time updates**: Use NiceGUI's `ui.timer()` at 2-second intervals to poll the SimulatedZoneState and update the zone visualization. This is simpler than WebSocket/SSE and sufficient for simulated telemetry that generates every 1-5 seconds
- **CSS animations for actuator feedback**: Use `ui.add_css()` with `@keyframes` for water-flow, fan-spin, heater-glow, and lamp-toggle animations. Toggle CSS classes on SVG/div elements via `element.classes(add=...)/remove=...)` combined with `ui.run_javascript()` for smooth transitions. This avoids a heavy animation library
- **Mode selector as a top-level dropdown**: A `ui.select()` on the simulator page that switches between "Internal Simulator" and "Wokwi/MQTT" modes. Mode state is per-session, stored in the page function scope. The mode determines whether command execution routes to SimulatedZoneState (Mode 1) or CommandPublisher/MQTT (Mode 2)
- **In-place action approval on AI chat page**: Wire `on_approve`/`on_reject` callbacks on `proposed_action_card` in the AI chat page, following the same POST pattern as the control page. No redirect needed
- **Zone visualization as SVG zones**: Use `ui.html()` to render an SVG-based zone layout showing metric gauges and actuator icons. Update via `set_content()` on timer ticks. CSS animation classes are toggled by modifying class attributes in the SVG string

---

## Open Questions

### Resolved During Planning

- **Real-time mechanism**: `ui.timer()` polling at 2-second intervals — sufficient for simulator-mode telemetry, avoids WebSocket complexity
- **Animation approach**: CSS keyframe animations toggled via class changes — lighter than canvas/SVG animation libraries, native to NiceGUI
- **Approval location**: In-place on AI chat page, not redirect to control page
- **Mode state scope**: Per-session on simulator page, not global

### Deferred to Implementation

- **Animation timing details**: Exact easing curves, duration values, and visual styles for each actuator type — decide during implementation when visual feedback can be iterated
- **Zone layout design**: How many zones to display simultaneously and the SVG arrangement — iterate during implementation

---

## Implementation Units

- U1. **SimulatedZoneState Service**

**Goal:** Create an in-memory service that holds mutable zone state, accepts command mutations (pump on/off, fan power, etc.), and produces telemetry values that reflect those mutations over time.

**Requirements:** R1, R2

**Dependencies:** None

**Files:**
- Create: `app/services/simulator/zone_state.py`
- Modify: `app/services/simulator/__init__.py`
- Modify: `app/api/simulator.py`
- Test: `tests/unit/test_simulator_zone_state.py`

**Approach:**
- `SimulatedZoneState` holds per-zone actuator states (pump on/off + remaining duration, fan power, heater power, lamp on/off) and current metric values with decay functions
- When a command is applied (e.g., "pump on for 30 seconds"), the state records the activation, start time, and duration
- Telemetry generation queries the state: soil_moisture gradually increases while pump is active, temperature rises with heater, etc.
- All state mutations and reads use `asyncio.Lock` to prevent torn reads between the background telemetry task and API-triggered command mutations
- The existing `_metric_value()` function is refactored to consult `SimulatedZoneState` instead of computing purely from scenario config
- State is keyed by (group_id, greenhouse_id, zone_id) to match the simulator's zone hierarchy

**Patterns to follow:**
- `app/services/simulator/scenarios.py` — existing scenario generators
- `app/models/command.py` — CommandLog status state machine pattern

**Test scenarios:**
- Happy path: apply watering command → soil_moisture increases within next telemetry tick
- Happy path: apply ventilation command → air_humidity decreases, temperature stabilizes
- Edge case: apply command with duration → effects taper off after duration expires
- Edge case: apply command to non-existent zone → no-op or error
- Error path: apply command when simulator is not running → state stored, applied when next tick runs
- Integration: start simulator → generate telemetry → apply command via API → next telemetry tick reflects state change

**Verification:**
- Simulator telemetry values change after command application
- Commands with duration expire and state returns to baseline
- Multiple overlapping commands (e.g., pump + heater) combine effects correctly

---

- U2. **Mode-Aware Command Execution Routing**

**Goal:** Route command execution based on operational mode — in Simulator mode, apply commands to SimulatedZoneState; in MQTT mode (Plan 2), publish to MQTT.

**Requirements:** R2, R5

**Dependencies:** U1

**Files:**
- Create: `app/services/simulator/mode_router.py`
- Modify: `app/services/command_service.py`
- Modify: `app/models/command.py`
- Create: `migrations/versions/XXXX_add_mode_to_command_log.py`
- Test: `tests/unit/test_mode_router.py`

**Approach:**
- Add `mode` column to `CommandLog` model: `simulator` | `mqtt` (default: `simulator`)
- `CommandService.execute()` checks the mode: if `simulator`, calls `SimulatedZoneState.apply_command()`; if `mqtt`, calls `CommandPublisher.publish()` (existing behavior)
- `ModeRouter` encapsulates the dispatch logic so command_service stays clean
- Mode is determined at propose-time from the current simulator page session mode
- The mode field defaults to `simulator` for backward compatibility

**Patterns to follow:**
- `app/services/command_publisher.py` — existing MQTT publishing pattern
- `app/services/safety_validator.py` — validation and routing pattern

**Test scenarios:**
- Happy path: propose command in simulator mode → approve → applies to SimulatedZoneState
- Happy path: propose command in mqtt mode → approve → publishes to MQTT
- Edge case: propose command in one mode, switch mode before approval → command executes in its original mode
- Error path: execute command when simulator mode zone state is missing → error logged, command marked failed

**Verification:**
- Commands route to the correct execution backend based on mode
- Mode field is persisted on the CommandLog
- Switching modes does not affect pending commands

---

- U3. **Zone Visualization Component with Animations**

**Goal:** Build a NiceGUI component that renders greenhouse zones as interactive SVG/CSS visualizations with metric gauges and actuator icons, and supports animated state transitions.

**Requirements:** R1, R3, R4

**Dependencies:** U1

**Files:**
- Create: `app/ui/components/zone_visualization.py`
- Create: `app/ui/static/animations.css` (keyframe definitions)
- Test: `tests/unit/test_zone_visualization.py`

**Approach:**
- `ZoneVisualization` renders one or more zone cards, each built from separate `ui.html()` elements per metric value and per actuator icon — never using a single SVG string replacement for the whole card
- Each zone card shows: zone name, 5 metric values (temp, humidity, soil_moisture, co2, light) as colored badge elements, and 4 actuator state indicators (pump, fan, heater, lamp)
- Animations are CSS keyframes loaded via `ui.add_css(shared=True)`:
  - `water-flow`: blue pulsing/wave animation on the pump icon
  - `fan-spin`: rotation animation on the fan icon
  - `heater-glow`: red/orange pulsing glow on the heater icon
  - `lamp-blink`: yellow flash on the lamp icon
- Actuator state changes trigger class additions/removals on individual SVG elements via `ui.run_javascript()` targeting specific element IDs. This preserves running CSS animations because innerHTML is not replaced
- Metric values update by calling `set_text()` on per-metric badge elements, or `run_javascript()` to update text content of individual SVG text nodes — never via `set_content()` on the parent container
- Component exposes `update_zone(zone_id, state)` method called from the timer callback; only changed values trigger DOM updates

**Execution note:** Start with a static SVG layout, then add update logic, then add CSS animations iteratively.

**Patterns to follow:**
- `app/ui/components/telemetry_cards.py` — metric badge styling and color thresholds
- NiceGUI `ui.html()` for arbitrary HTML/SVG content
- NiceGUI `ui.add_css()` for global keyframe definitions

**Test scenarios:**
- Happy path: render zone with initial state → metrics and actuator icons display correctly
- Happy path: call `update_zone()` → metric values update in the DOM
- Happy path: activate pump animation → CSS class added, water-flow animation plays
- Edge case: update zone that doesn't exist in visualization → no-op
- Error path: timer callback when component is disconnected → graceful no-op

**Verification:**
- Zone visualization renders with all 5 metrics and 4 actuator indicators
- CSS animations play when actuators are activated
- Metric values reflect SimulatedZoneState data

---

- U4. **Simulator Page Refactor with Mode Selector and Live Visualization**

**Goal:** Refactor the simulator page to include a mode selector, the zone visualization component, and a timer-driven live data refresh loop.

**Requirements:** R1, R3, R4, R5

**Dependencies:** U1, U3

**Files:**
- Modify: `app/ui/pages/simulator.py`
- Modify: `app/api/simulator.py` (add zone state API endpoint)
- Create: `app/api/simulator_state.py`
- Test: `tests/unit/test_simulator_page.py`

**Approach:**
- Add mode selector (`ui.select` with options: "Internal Simulator", "Wokwi/MQTT") at the top of the simulator page
- In Simulator mode, show the ZoneVisualization below the existing controls
- When simulator is started, begin `ui.timer(2.0, refresh_zone_state)` that polls the `/api/simulator/zones` endpoint (owned by U6) returning current SimulatedZoneState for each zone
- The timer callback calls `zone_viz.update_zone(zone_id, state)` for each active zone
- The mode selector value is passed to `CommandService.propose()` in future command proposals from this page
- When mode switches to Wokwi/MQTT, the zone visualization hides (or shows a "Connect your Wokwi device" notice for Plan 2)

**Patterns to follow:**
- `app/ui/pages/dashboard.py` — page layout with data loading and ECharts
- NiceGUI `ui.timer()` for periodic refresh
- `app/ui/pages/simulator.py` — existing page structure

**Test scenarios:**
- Happy path: start simulator → zone visualization appears → metrics update every 2s
- Happy path: switch mode to Wokwi/MQTT → visualization hides, notice shows
- Integration: approve command from AI chat → zone state changes → visualization updates on next timer tick
- Edge case: stop simulator → zone visualization shows "stopped" state
- Edge case: page refresh while simulator running → state reloaded from SimulatedZoneState API

**Verification:**
- Simulator page renders mode selector and zone visualization
- Zone metrics update in real-time when simulator is running
- Mode switch changes the UI and command routing

---

- U5. **AI Chat In-Place Action Approval**

**Goal:** Wire the proposed_action_card approval/rejection callbacks on the AI chat page so users can approve or reject AI-proposed actions directly without navigating away.

**Requirements:** R2, R6

**Dependencies:** U2

**Files:**
- Modify: `app/ui/pages/ai_chat.py`
- Modify: `app/ui/components/proposed_action_card.py` (add status refresh after approval)

**Approach:**
- In `ai_chat.py`, when rendering `proposed_action_card(action)`, pass `on_approve` and `on_reject` callbacks that:
  1. POST to `/api/commands/{id}/approve` (or `/reject`)
  2. The approval endpoint calls `CommandService.execute()` which synchronously mutates `SimulatedZoneState` before returning the HTTP response. This guarantees the state update is visible to any tab's timer poll on the very next refresh cycle
  3. Refresh the card's status badge in the callback
- Follow the same pattern as the control page which already has working approval logic
- After approval, the chat page shows a brief confirmation notification via `ui.notify()`

**Patterns to follow:**
- `app/ui/pages/control.py` — existing approval flow with `POST /api/commands/{id}/approve`
- `app/ui/components/proposed_action_card.py` — existing `on_approve`/`on_reject` callback signature

**Test scenarios:**
- Happy path: click "Approve" on proposed_action_card → command transitions to executed → card shows "Executed" badge
- Happy path: click "Reject" on proposed_action_card → command transitions to rejected → card shows "Rejected" badge
- Edge case: approve an already-expired command → error notification shown
- Integration: approve watering command in simulator mode → SimulatedZoneState changes → zone visualization reflects change on next tick

**Verification:**
- AI chat proposed actions can be approved/rejected in-place
- Card status updates after approval/rejection
- Approved commands in simulator mode affect SimulatedZoneState

---

- U6. **Simulator API Endpoint for Zone State**

**Goal:** Add a REST API endpoint that exposes the current SimulatedZoneState so the frontend can poll it, and integrate it with the existing simulator start/stop lifecycle.

**Requirements:** R4

**Dependencies:** U1

**Files:**
- Create: `app/api/simulator_state.py`
- Modify: `app/main.py` (register new router)
- Modify: `app/api/simulator.py` (integrate zone state into start/stop)

**Approach:**
- Sole owner of the `GET /api/simulator/zones` endpoint (U4 consumes it, does not create it)
- Returns a list of `ZoneStateRead` schemas with current metric values and actuator states
- The `SimulatorBackgroundTask` holds a reference to the `SimulatedZoneState` singleton and updates it on each tick
- When the simulator starts, `SimulatedZoneState` is initialized with the zone topology (groups × greenhouses × zones from the start config)
- When the simulator stops, `SimulatedZoneState` is reset
- `SimulatedZoneState` is a single-instance service; concurrent start requests are idempotent (reject if already running with different config)
- `ZoneStateRead` schema includes: zone_id, group_id, greenhouse_id, all 5 metrics, all 4 actuator states, and active animation flags

**Patterns to follow:**
- `app/api/simulator.py` — existing simulator endpoints
- `app/schemas/telemetry.py` — telemetry schema patterns

**Test scenarios:**
- Happy path: GET /api/simulator/zones returns all zone states when simulator is running
- Happy path: GET /api/simulator/zones returns empty list when simulator is stopped
- Edge case: simultaneous start requests → idempotent, returns existing state
- Integration: start simulator → apply command → GET zones → reflects command effect

**Verification:**
- API endpoint returns correct zone states
- Zone state reflects command mutations
- Lifecycle (start/stop) correctly manages state

---

## System-Wide Impact

- **Interaction graph:** The proposed action pipeline now has two execution paths: simulator mode (SimulatedZoneState) and MQTT mode (CommandPublisher). `CommandService.execute()` is the dispatch point. The mode router affects all command execution flows.
- **Error propagation:** Command execution errors in simulator mode are logged and the command is marked `failed`. In MQTT mode, existing error handling applies. Mode router catches exceptions and ensures commands don't silently fail.
- **State lifecycle risks:** SimulatedZoneState is in-memory and lost on server restart. This is acceptable for a simulation/demo context. Commands in the database persist across restarts but their in-memory effects do not.
- **API surface parity:** The `/api/simulator/zones` endpoint is new. The existing `/api/simulator/start`, `/stop`, `/status` endpoints remain unchanged. The `/api/commands/{id}/approve` endpoint gains mode-aware routing but retains the same request/response contract.
- **Integration coverage:** The full flow (AI chat → propose → approve → SimulatedZoneState → telemetry → visualization → timer update) crosses agent, service, API, and UI layers. Integration tests should exercise this end-to-end.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| SimulatedZoneState in-memory — lost on server restart | Acceptable for simulator/demo context. CommandLog in DB persists for audit. Document this as a known limitation. |
| CSS animation performance with many zones (e.g., 10 groups × 20 greenhouses × 20 zones = 4000 zones) | Paginate or filter zone display to show one greenhouse at a time. Default config is 1 group × 3 greenhouses × 4 zones = 12 zones, well within performance bounds. |
| Timer polling interval vs. animation smoothness | 2-second telemetry polling is sufficient for state updates. CSS animations run at 60fps independently. Only state class toggles happen at 2s intervals. |
| Mode stored per-session — multiple tabs may see different modes | This is by design. Each user selects their own mode. Commands persist their mode in the database. |

---

## Documentation / Operational Notes

- The `animations.css` file must be mounted in Docker dev mode (`compose.override.yml`) and copied in the production Dockerfile, following the same pattern as the `locales/` directory
- API documentation for `/api/simulator/zones` should be added to any existing API docs
- The `mode` field on `CommandLog` is a new database column requiring a migration

---

## Sources & References

- Codebase: `app/api/simulator.py`, `app/ui/pages/simulator.py`, `app/ui/pages/ai_chat.py`, `app/ui/components/proposed_action_card.py`, `app/services/command_service.py`, `app/services/ai_agent/tools/proposed_action_tools.py`
- NiceGUI timer API: `ui.timer(interval, callback, active=True)`
- NiceGUI SVG/HTML: `ui.html(content)`, `ui.add_css(css)`
- Institutional learning: NiceGUI must use `ui.run_with()`, not `ui.run()`