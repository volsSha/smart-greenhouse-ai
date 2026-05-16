---
title: feat: Add persisted real control mode
type: feat
status: active
date: 2026-05-15
---

# feat: Add persisted real control mode

## Summary

Add a database-backed project-wide control mode so `/control` is no longer just demo/emulation: MQTT mode routes approved commands to remote devices, while simulator mode routes approved commands into the internal simulator and makes actuator effects visible through simulator state and persisted telemetry.

---

## Problem Frame

The current `/control` UI now renders an operator panel with SVG zones and actuator controls, but its no-data demo fallback can make the page look functional even when it is not connected to a real execution backend. The user wants control behavior to be explicit and persistent: a settings-level mode chooses whether controls operate remote MQTT devices or the internal simulator, and simulator control must be two-way enough that control-panel changes affect simulator state and downstream data.

---

## Requirements

- R1. Add a project-wide control mode setting saved in the database with valid values `mqtt` and `simulator`.
- R2. Expose the control mode on `/settings` so the user can choose MQTT remote control or simulator control across the project.
- R3. `/control` must read and display the active persisted control mode instead of silently relying on demo behavior or schema defaults.
- R4. Commands created from normal public/UI proposal flows must store the active persisted mode on the command row at proposal time so pending commands keep their original execution target.
- R5. Public command proposal clients must not be able to bypass the persisted project mode by posting a conflicting command `mode` value.
- R6. In MQTT mode, approved `/control` commands must publish through the existing MQTT command execution path for remote devices.
- R7. In simulator mode, approved `/control` commands must route through the existing simulator mode router and mutate internal simulator actuator state.
- R8. Simulator mode must be visibly two-way: actuator changes made from `/control` must affect simulator state reads and telemetry values written by the simulator loop.
- R9. The UI must clearly distinguish MQTT mode, simulator mode, and the offline/demo fallback state so operators do not mistake fake local proposals or broker publish acknowledgements for physical actuation.
- R10. Existing safety validation and approval-before-execution behavior must remain intact unless a separate future requirement explicitly changes that safety posture.

---

## Scope Boundaries

- Do not bypass command proposal, validation, approval, or execution safety gates in this plan.
- Do not add direct browser-to-MQTT publishing; MQTT publishing remains server-side through the existing command execution service.
- Do not provision MQTT brokers, firmware, hardware devices, or Wokwi projects.
- Do not redesign the whole `/simulator` page; only adjust it where needed to consume/show the persisted control mode or prove two-way simulator sync.
- Do not make simulator state durable across app restarts; persisted mode may remain `simulator`, but the simulator runtime itself is still started/stopped explicitly.
- Do not remove the existing per-command `mode` column; it remains the audit record for how each command will execute.
- Do not conflate `/simulator` telemetry-output selection with project control mode; simulator page MQTT/Wokwi telemetry controls remain a separate concept.
- Do not add production authentication in this iteration, but do document and preserve the current trusted-local/development deployment assumption for settings and approval endpoints.

### Deferred to Follow-Up Work

- Auto-starting the simulator when the user selects simulator mode: defer until scenario/default-runtime expectations are defined.
- Broker/device health gates before saving MQTT mode: defer; this plan can show status and let execution failures surface through the existing command path.
- Role-based restrictions for who may change control mode: defer only as a production-hardening item; the implementation must still avoid adding new unauthenticated bypasses and must document that remote MQTT use requires a trusted deployment boundary.
- Persistent simulator actuator snapshots across restarts: defer because current simulator architecture is intentionally in-memory.

---

## Context & Research

### Relevant Code and Patterns

- `app/models/model_settings.py` is the existing singleton database-backed settings model.
- `app/repositories/model_settings_repository.py` bootstraps and updates the singleton settings row.
- `app/api/settings.py` exposes settings read/update endpoints already used by the UI.
- `app/schemas/settings.py` defines the settings API contracts.
- `app/ui/pages/settings.py` renders the existing settings page.
- `app/schemas/commands.py` already supports command `mode` with valid values `simulator` and `mqtt`.
- `app/models/command.py` already persists per-command mode on `command_log`.
- `app/services/command_service.py` freezes command fields at proposal time and dispatches execution based on command mode during approval.
- `app/services/command_publisher.py` publishes approved MQTT commands to scoped device topics.
- `app/services/simulator/mode_router.py` routes simulator-mode commands into `SimulatedZoneState`.
- `app/services/simulator/zone_state.py` stores in-memory actuator state and computes actuator effects on metrics.
- `app/api/simulator.py` and `app/api/simulator_state.py` expose simulator lifecycle, state, and telemetry loop behavior.
- `app/ui/pages/control.py` is the `/control` page that must read the mode and include it in proposal payloads.
- `app/ui/pages/simulator.py` has a page-local telemetry-output/runtime selector today; it should remain distinct from project control mode while showing persisted control mode as separate context where useful.
- `tests/integration/test_settings_api.py`, `tests/unit/test_command_mqtt_mode.py`, `tests/unit/test_mode_router.py`, and `tests/unit/test_simulator_zone_state.py` are the closest existing tests.

### Institutional Learnings

- `docs/solutions/ui-bugs/nicegui-i18n-docker-hot-reload-2026-05-11.md`: NiceGUI selectors emit display labels, so mode selectors must map labels back to stable values explicitly.
- `docs/solutions/ui-bugs/docker-compose-fastapi-nicegui-dashboard-launch-fix-2026-05-07.md`: use supported NiceGUI APIs and wrapper callbacks for handlers referenced before definition.

### External References

- No external research is needed. The repo already contains the settings singleton, command mode, MQTT publisher, and simulator mode router patterns needed for this change.

---

## Key Technical Decisions

- Store the project-wide control mode in the existing settings singleton rather than adding a second settings table: this follows the current database-backed settings pattern and keeps `/settings` as the single project preferences surface.
- Add a dedicated control-mode settings update contract instead of overloading the chat-model settings update shape: the existing selected-model update validates model catalog data, while control mode needs a small independent validation path.
- Treat persisted control mode as the server-side source of truth for normal public/UI proposals: `/control` and ordinary API callers should not be able to override the project-wide mode by submitting a conflicting command mode.
- Freeze mode on the command at proposal time: a pending command proposed while MQTT mode is active should still execute as MQTT even if the project setting changes before approval, but approval UI/API must surface or block current-setting mismatches so approvers do not accidentally execute old-mode commands.
- Keep command-level mode for auditability and execution dispatch: the setting chooses the mode for new commands, while each command row records what will happen when approved.
- Do not auto-start the simulator when simulator mode is selected: simulator runtime lifecycle remains explicit, and `/control` should disable proposal controls with a clear not-running state when simulator mode is selected but the simulator is not running.
- Preserve server-side validation as authoritative: UI mode badges and selector bounds are usability features, not safety controls.
- Make demo fallback visibly offline-only: demo data may help an empty development database render the page, but it must not be presented as MQTT or simulator control.
- Treat MQTT broker publish as delivery to broker, not physical confirmation: UI copy and command displays must not imply device actuation was physically confirmed unless a separate acknowledgement path exists.

---

## Open Questions

### Resolved During Planning

- Should control mode be saved per project or only inside `/control` page state? Save it in the database as project-wide settings so `/settings`, `/control`, and `/simulator` do not drift.
- Should mode be resolved at proposal time or approval time? Resolve at proposal time and store it on the command row to avoid surprise execution target changes for pending commands.
- Should simulator mode auto-start the simulator? No; show a clear simulator-not-running state and use existing explicit simulator start controls.
- Should MQTT mode require a live broker before saving? No; allow saving the intended remote mode, then surface publish failures through the existing command execution path.
- Should `/simulator` page mode be replaced by project control mode? No; keep telemetry-output/runtime selection distinct and add project control mode as separate context where useful.
- Should settings-load failure on `/control` fall back to MQTT? No; disable proposal creation until settings load succeeds so schema defaults cannot accidentally publish remotely.

### Deferred to Implementation

- Exact UI copy for mode warnings and demo/offline labels: choose concise wording during implementation and translate via `_()`.
- Exact placement of the settings mode card: keep it on `/settings`, near other project-level settings, but fit it into the current page layout during implementation.
- Exact simulator warning condition: implementation should use the existing simulator status/state API available at the time of wiring.

---

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

```mermaid
flowchart TD
    A[/settings] --> B[save project control mode]
    B --> C[(settings singleton)]
    D[/control loads] --> E[read project control mode]
    E --> F[show active mode badge and warnings]
    F --> G[operator creates proposal]
    G --> H[command stores mode snapshot]
    H --> I[approver approves command]
    I --> J{command mode}
    J -->|mqtt| K[server publishes MQTT command]
    J -->|simulator| L[mode router mutates simulator state]
    L --> M[simulator state API shows actuator change]
    L --> N[simulator telemetry loop writes affected metrics]
```

---

## Implementation Units

### U1. Persist project-wide control mode in settings

**Goal:** Add a database-backed control mode field to the settings singleton and expose it through the settings repository and API contracts.

**Requirements:** R1, R4, R5

**Dependencies:** None

**Files:**
- Modify: `app/models/model_settings.py`
- Modify: `app/repositories/model_settings_repository.py`
- Modify: `app/schemas/settings.py`
- Modify: `app/api/settings.py`
- Create: `migrations/versions/0005_add_control_mode_to_model_settings.py`
- Test: `tests/integration/test_settings_api.py`
- Test: `tests/integration/test_migrations.py`

**Approach:**
- Add a non-null control mode setting with a default of MQTT so existing command behavior remains compatible, but make `/control` display that mode explicitly before any proposal can be created.
- Validate accepted values at the API/schema boundary and reject anything other than MQTT or simulator.
- Bootstrap missing settings rows with the same default so fresh databases and tests behave consistently.
- Add a dedicated control-mode update schema/endpoint or PATCH-style branch so control-mode saves do not require `selected_chat_model` and do not trigger chat-model catalog validation.
- Derive command mode server-side for normal public proposal creation from persisted settings, or reject conflicting client-supplied mode values; do not let ordinary clients bypass project-wide mode.
- Preserve any truly internal explicit-mode path only if it is clearly separated from the public proposal contract and covered by tests.

**Execution note:** Add migration/API coverage before wiring UI consumers so mode storage is stable first.

**Patterns to follow:**
- `app/models/model_settings.py` singleton settings fields.
- `app/repositories/model_settings_repository.py` bootstrap/update pattern.
- `app/api/settings.py` validation and commit behavior.
- `tests/integration/test_settings_api.py` settings endpoint coverage.

**Test scenarios:**
- Happy path: a fresh settings row bootstraps with MQTT control mode and settings responses expose it explicitly.
- Happy path: updating settings to simulator persists and a subsequent GET returns simulator without requiring a selected chat model payload.
- Happy path: updating settings back to MQTT persists and a subsequent GET returns MQTT without triggering chat-model catalog validation.
- Error path: invalid control mode values are rejected and do not mutate the stored setting.
- Error path: public command proposal with persisted simulator mode and request payload `mode=mqtt` is rejected or stored as simulator according to the chosen server-side contract.
- Migration: existing settings rows receive the default control mode without dropping or recreating existing data.

**Verification:**
- The database has one persisted project-wide control mode value.
- Settings API consumers can read and update the mode without touching command rows directly.

---

### U2. Add project control mode UI on settings page

**Goal:** Let the user choose MQTT or simulator mode from `/settings` and make the saved choice durable across page reloads and sessions.

**Requirements:** R2, R9

**Dependencies:** U1

**Files:**
- Modify: `app/ui/pages/settings.py`
- Modify: `locales/messages.pot` only if project workflow requires extraction after adding strings
- Modify: `locales/uk/LC_MESSAGES/messages.po` only if new translated strings are maintained immediately
- Test: `tests/system/test_settings_page_scope.py`
- Test: `tests/integration/test_settings_api.py`

**Approach:**
- Add a clear settings section for control mode with MQTT described as remote device control and simulator described as internal two-way simulator control.
- Use explicit label-to-value mapping for the selector so translated display labels never become backend values.
- Save mode changes through the existing settings API and refresh visible state after save.
- Keep the setting project-wide, not per browser session.

**Patterns to follow:**
- Existing `/settings` page API-client and notification patterns.
- NiceGUI selector label mapping guidance from `docs/solutions/ui-bugs/nicegui-i18n-docker-hot-reload-2026-05-11.md`.

**Test scenarios:**
- Happy path: settings page source includes a control-mode section and does not expose secrets.
- Happy path: selecting simulator sends the simulator value to the settings API and shows the saved mode after refresh.
- Edge case: translated display labels still map to stable MQTT/simulator values.
- Error path: failed save keeps the previous visible saved state and shows an error notification.

**Verification:**
- A user can change the project control mode from `/settings` and observe that the value survives reload.

---

### U3. Apply persisted control mode to `/control` proposals

**Goal:** Make `/control` read the saved mode, display it, and include that mode in new command proposals so real execution follows the selected backend.

**Requirements:** R3, R4, R5, R9, R10

**Dependencies:** U1

**Files:**
- Modify: `app/ui/pages/control.py`
- Modify: `app/ui/components/actuator_controls.py`
- Modify: `app/ui/components/zone_control_drawer.py`
- Test: `tests/unit/test_actuator_controls.py`
- Test: `tests/integration/test_control_operator_panel.py`
- Test: `tests/unit/test_command_mqtt_mode.py`

**Approach:**
- Load settings when `/control` initializes and show a prominent active-mode badge near the scope controls or drawer.
- Disable proposal controls until settings load succeeds; never let settings-load failure fall through to `CommandPropose` schema defaults.
- Pass the active mode into actuator proposal payload construction for UI clarity, while the server still derives or validates mode against persisted settings for public proposal requests.
- Keep demo fallback visibly offline-only and prevent it from implying remote MQTT or simulator execution; assign this fallback labeling to this unit because it owns `/control` mode display.
- If simulator mode is active but simulator runtime is stopped, disable proposal controls and show a start/open-simulator path rather than creating proposals that can only fail at approval time.
- Refresh settings when the user refreshes the control page so `/settings` changes become visible without restarting the app.
- Preserve proposal-only UI behavior: the first operator action creates a command proposal; execution still happens through approval.
- Always show the frozen command execution mode on pending proposal cards; when it differs from current project mode, surface a mismatch warning before approval.

**Patterns to follow:**
- Current `/control` API loading and notification flow.
- `app/schemas/commands.py` mode validation.
- `tests/unit/test_command_mqtt_mode.py` mode dispatch expectations.

**Test scenarios:**
- Happy path: when settings mode is MQTT, a pump proposal from selected-zone controls includes MQTT mode for display/payload clarity and the command stores MQTT.
- Happy path: when settings mode is simulator, a fan/heater proposal includes simulator mode for display/payload clarity and the command stores simulator.
- Edge case: changing settings after a proposal is created does not alter that pending command's stored mode, and the pending card shows the frozen mode.
- Edge case: demo fallback renders as offline/demo and does not claim MQTT or simulator execution.
- Error path: settings API failure on `/control` load disables proposal controls and does not create commands with schema-default MQTT mode.
- Error path: simulator mode with simulator stopped disables proposal controls or blocks proposal creation before approval.
- Safety invariant: creating a proposal does not call approve or publish directly.

**Verification:**
- `/control` visibly states whether new proposals will target MQTT or simulator.
- New command rows created from `/control` carry the mode selected in settings.

---

### U4. Align simulator two-way execution and telemetry persistence

**Goal:** Ensure simulator-mode commands from `/control` mutate simulator actuator state and those effects become visible through simulator state reads and persisted telemetry.

**Requirements:** R7, R8, R9, R10

**Dependencies:** U1, U3

**Files:**
- Modify: `app/api/simulator.py`
- Modify: `app/api/simulator_state.py`
- Modify: `app/services/simulator/zone_state.py` only if existing state/effect behavior needs a small adjustment
- Modify: `app/ui/pages/simulator.py`
- Test: `tests/unit/test_mode_router.py`
- Test: `tests/unit/test_simulator_zone_state.py`
- Test: `tests/integration/test_command_approval_execution.py`

**Approach:**
- Use the existing command approval path for simulator execution: approved simulator-mode commands route through the mode router into in-memory simulator state.
- Enforce an identity invariant across control proposals, simulator state, and telemetry writes: the same canonical group/greenhouse/zone IDs selected in `/control` must be used by simulator state lookup and telemetry rows.
- Verify the simulator telemetry loop reads actuator-adjusted values from simulator state when state exists, so pump/fan/heater/lamp effects are written to telemetry storage.
- On `/simulator`, keep telemetry-output/runtime selection distinct from project control mode; rename or clarify the page-local selector if needed, and add a separate read-only project control mode badge only where it helps.
- When persisted mode is simulator but the simulator is stopped, show a clear not-running state and fail clearly if an old pending simulator command reaches approval rather than inventing hidden simulator state.

**Patterns to follow:**
- `app/services/simulator/mode_router.py` route behavior.
- `app/services/simulator/zone_state.py` actuator effect and expiration behavior.
- `app/api/simulator_state.py` simulator lifecycle and telemetry loop.
- `app/ui/pages/simulator.py` polling and status display.

**Test scenarios:**
- Happy path: approved simulator-mode pump command marks pump active in simulator zone state for the exact selected group/greenhouse/zone IDs.
- Happy path: after simulator-mode pump command, simulator telemetry reads for soil moisture reflect actuator-adjusted values and carry the same zone ID.
- Happy path: approved simulator-mode heater/fan/lamp commands affect the expected simulator metrics and animation/state flags.
- Edge case: duration expiry deactivates simulator actuator state and later telemetry reflects the expired state.
- Error path: simulator-mode approval while simulator state is missing marks command failed or returns the existing simulator-not-running failure path clearly.
- Error path: simulator runtime does not contain the command's target zone, so approval fails clearly instead of creating hidden state for an unknown zone.
- Integration: `/control` proposal in simulator mode plus approval results in simulator state visible through simulator state API.

**Verification:**
- Simulator mode is genuinely two-way: control-panel approved commands change simulator state, and simulator-generated telemetry reflects those changes.

---

### U5. Preserve MQTT execution and improve operator feedback

**Goal:** Make MQTT mode clearly operate the existing remote-device execution path and expose publish failures/status to the operator without changing broker/device provisioning.

**Requirements:** R6, R9, R10

**Dependencies:** U1, U3

**Files:**
- Modify: `app/ui/pages/control.py`
- Modify: `app/ui/components/zone_control_drawer.py`
- Modify: `app/services/command_service.py` only if existing failure messages are too opaque for the UI to display usefully
- Test: `tests/unit/test_command_mqtt_mode.py`
- Test: `tests/integration/test_command_approval_execution.py`
- Test: `tests/integration/test_control_operator_panel.py`

**Approach:**
- In MQTT mode, keep approved command execution on the existing server-side publisher path and do not add browser-side MQTT clients.
- Display mode-specific guidance in `/control`: MQTT mode publishes to subscribed remote devices after approval; if no device is listening, broker publish can succeed without physical movement.
- Label MQTT publish success as broker delivery/command sent rather than physical confirmation unless an explicit device acknowledgement path exists.
- Ensure publish failures surface as failed command status or visible notifications through the existing command refresh path.
- Keep recent command and selected-zone pending/outcome displays mode-aware enough that operators can distinguish simulator commands from MQTT commands.
- Add an operational checklist for MQTT mode: credentials come from environment/secret storage, command topics are scoped through existing topic builders, broker ACL/TLS or trusted-network assumptions are documented, and command payloads/secrets are not logged.

**Patterns to follow:**
- `app/services/command_publisher.py` publish behavior.
- `app/services/command_service.py` execution status transitions.
- Current `/control` recent command refresh behavior.

**Test scenarios:**
- Happy path: approved MQTT-mode command calls the MQTT publisher and transitions to the existing success status while UI copy presents it as broker delivery, not physical confirmation.
- Error path: MQTT publish failure transitions the command to failed and `/control` can display the failed outcome after refresh.
- Edge case: MQTT mode with no real subscribed device still records broker publish success if broker accepts the message; UI copy does not promise physical movement confirmation.
- Security path: MQTT publishing uses scoped command topics and does not log credentials or secrets.
- Safety invariant: MQTT mode still requires approval before publish.

**Verification:**
- MQTT mode is real remote-control routing through the existing broker publisher, not local demo mutation.

---

### U6. End-to-end UI verification and regression coverage

**Goal:** Verify the complete persisted-mode workflow across settings, control, simulator, and command execution paths.

**Requirements:** R1, R2, R3, R4, R5, R6, R7, R8, R9, R10

**Dependencies:** U1, U2, U3, U4, U5

**Files:**
- Modify: `tests/integration/test_control_operator_panel.py`
- Modify: `tests/integration/test_settings_api.py`
- Modify: `tests/integration/test_command_approval_execution.py`
- Modify: `tests/system/test_no_direct_ai_actuation.py` only if new assertions are needed
- Test: browser/manual verification for `/settings`, `/control`, and `/simulator`

**Approach:**
- Cover the settings-to-control contract with integration tests: saved mode controls the mode attached to new proposals.
- Cover both execution branches: simulator mutation and MQTT publish.
- Keep source-level UI regression checks for static markers, but do not treat them as a replacement for live UI verification.
- Run live verification at `http://127.0.0.1:8080/settings`, `http://127.0.0.1:8080/control`, and `http://127.0.0.1:8080/simulator` after implementation.

**Patterns to follow:**
- Existing control operator panel test style.
- Existing command approval execution integration tests.
- Existing no-direct-actuation system tests.

**Test scenarios:**
- End-to-end: save simulator mode, open `/control`, create and approve a proposal, then observe simulator state/telemetry reflecting the actuator change.
- End-to-end: save MQTT mode, open `/control`, create and approve a proposal, then observe MQTT publisher path invoked and command status updated.
- Regression: proposal creation remains separate from approval/execution in both modes.
- Regression: settings failure, simulator-stopped state, and conflicting request mode all fail closed without reaching MQTT publish or simulator mutation.
- Regression: demo fallback remains visibly demo/offline and does not mask real mode failures.
- Browser: settings mode selection persists across reload and `/control` reflects the new value.

**Verification:**
- The exact requested local UI can be exercised with real persisted mode behavior instead of only local demo data.

---

## System-Wide Impact

- **Interaction graph:** `/settings` becomes the source for new command execution mode; `/control` reads settings and writes command proposals; command approval dispatches to MQTT or simulator based on the command's stored mode; simulator state and telemetry APIs expose simulator effects.
- **Error propagation:** invalid mode saves fail at the settings API; simulator-not-running failures surface during simulator-mode approval; MQTT publish failures surface through command execution status and UI refresh.
- **State lifecycle risks:** persisted simulator mode can survive app restarts while simulator in-memory state does not; UI must warn clearly instead of silently creating fake state.
- **API surface parity:** normal public proposal handling derives mode from settings or rejects conflicting client mode values; any internal explicit-mode path must be separated and tested.
- **Integration coverage:** tests must prove mode storage, proposal mode snapshotting, tamper resistance, MQTT execution, simulator execution, and telemetry effects across layers.
- **Deployment boundary:** until production auth exists, settings and approval endpoints remain trusted-local/development surfaces; remote MQTT deployments must be protected by network/reverse-proxy controls.
- **Unchanged invariants:** safety validation, command approval, MQTT topic structure, firmware subscription behavior, and AI no-direct-actuation rules remain unchanged.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Persisted simulator mode implies durability that current simulator state does not have | Keep simulator lifecycle explicit and show simulator-not-running state after restart/stop. |
| Mode changes surprise approvers reviewing pending commands | Freeze mode on each command at proposal time, always show command mode in pending/outcome cards, and warn/block when frozen mode differs from current setting. |
| Extending `model_settings` overloads an AI-named settings table | Accept for this iteration because it is the existing settings singleton; defer a broader app-settings rename/refactor. |
| Client-supplied mode bypasses the project setting | Derive mode server-side for public proposal flows or reject mismatches; cover tampered payloads in integration tests. |
| MQTT publish success is mistaken for physical device confirmation | UI copy should say MQTT mode publishes to subscribed devices after approval, not that hardware movement is confirmed. |
| Demo fallback continues to hide missing real data | Label demo/offline mode prominently and do not represent demo proposals as MQTT or simulator execution. |
| Simulator telemetry does not reflect actuator effects | Add focused integration/unit coverage around simulator command approval and telemetry-value generation. |

---

## Documentation / Operational Notes

- Update `docs/ROUTES.md` only if it documents `/settings`, `/control`, or `/simulator` behavior.
- If new visible strings are added, run the repository's translation extraction/compile workflow before final verification.
- Add a `docs/solutions/` note after implementation if the persisted control-mode pattern or simulator two-way sync becomes a reusable pattern.
- Operators need MQTT broker plus subscribed firmware/device for real remote actuation; simulator mode only affects the internal simulator runtime.
- MQTT mode should only be used in trusted deployments with broker ACLs/TLS or an explicitly trusted local network, and settings/approval APIs must not be exposed publicly without an auth boundary.

---

## Sources & References

- Related plan: `docs/plans/2026-05-15-002-feat-control-operator-panel-plan.md`
- Related requirements: `docs/brainstorms/2026-05-15-control-operator-panel-requirements.md`
- Related code: `app/models/model_settings.py`
- Related code: `app/repositories/model_settings_repository.py`
- Related code: `app/api/settings.py`
- Related code: `app/schemas/settings.py`
- Related code: `app/ui/pages/settings.py`
- Related code: `app/ui/pages/control.py`
- Related code: `app/schemas/commands.py`
- Related code: `app/models/command.py`
- Related code: `app/services/command_service.py`
- Related code: `app/services/command_publisher.py`
- Related code: `app/services/simulator/mode_router.py`
- Related code: `app/services/simulator/zone_state.py`
- Related code: `app/api/simulator.py`
- Related code: `app/api/simulator_state.py`
- Related tests: `tests/integration/test_settings_api.py`
- Related tests: `tests/unit/test_command_mqtt_mode.py`
- Related tests: `tests/unit/test_mode_router.py`
- Related tests: `tests/unit/test_simulator_zone_state.py`
- Related tests: `tests/integration/test_command_approval_execution.py`
