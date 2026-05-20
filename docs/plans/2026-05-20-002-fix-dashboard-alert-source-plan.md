---
title: "fix: Use persisted alerts on dashboard"
status: active
created: 2026-05-20
updated: 2026-05-20
type: fix
---

# fix: Use persisted alerts on dashboard

## Problem Frame

The dashboard "Active Alerts" panel currently renders raw telemetry anomaly rows as alert cards. The anomaly endpoint returns out-of-range InfluxDB readings with fields such as `_time`, `_value`, `metric`, `greenhouse_id`, and `zone_id`, but no `title` or `message`. `alert_panel` therefore falls back to `Unknown Alert`, and sustained out-of-range telemetry can produce up to 100 near-duplicate cards.

The design correction is to make "Active Alerts" reflect persisted `Alert` records from PostgreSQL (`alert_log`) and keep raw telemetry anomalies out of that panel. If anomalies remain useful on the dashboard, they should be shown as a distinct normalized/aggregated signal, not as active alerts.

---

## Scope Boundaries

### In Scope

- Add a minimal grouped alerts API backed by `AlertRepository` for dashboard active-alert reads and dismissal writes.
- Update dashboard alert loading to use persisted active alerts instead of `/telemetry/anomalies`.
- Update alert identity and dismissal behavior to use persisted alert IDs/status.
- Preserve the telemetry anomalies endpoint for API consumers and future analytics.
- Remove raw anomaly rows from the Active Alerts panel; do not add a new anomaly widget in this fix.
- Add tests for the API contract, dashboard transformation behavior, and repository/API integration points.
- Add or update English/Ukrainian translations for any new user-facing labels.

### Out of Scope

- Database schema changes or migrations. The `Alert` model and repository already exist.
- Reworking threshold alert generation logic.
- Removing the existing telemetry anomalies endpoint.
- Building a full alert-management page.
- Changing simulator or MQTT telemetry generation.

### Deferred Follow-Up Work

- Add a separate "Recent anomalies" dashboard widget that aggregates raw anomaly samples by metric/zone/time window.
- Add alert severity/status filters or tabs if users need triage workflows beyond active alerts.
- Add solution documentation after implementation if the final fix reveals a reusable pattern for UI data-source separation.

---

## Key Technical Decisions

1. **Use persisted alerts as dashboard source of truth**
   - `alert_log` rows already carry `title`, `message`, `severity`, `status`, `source`, `created_at`, and optional scope IDs.
   - This matches the semantics of "Active Alerts" better than raw telemetry anomaly samples.

2. **Expose a minimal alerts API for dashboard needs**
   - Add `app/api/alerts.py` with `GET /api/groups/{group_id}/alerts?status=active` and `PATCH /api/groups/{group_id}/alerts/{alert_id}` for dismissal only.
   - Follow existing router/session patterns from `app/api/greenhouses.py` and router registration in `app/main.py`.
   - Require the same authentication/session access pattern as existing group-scoped APIs, and verify every returned or updated alert belongs to `group_id`.

3. **Persist dismissal as alert acknowledgement, without resolving the condition**
   - The dashboard currently stores dismissals in page-local memory, so alerts reappear after reload/session changes.
   - For persisted alerts, dismissal should call an API update that changes `status` to `dismissed`; "Dismiss all" should update all currently displayed active alert IDs.
   - This plan does not redefine whether the underlying hazardous condition is resolved; threshold evaluation must continue creating or reactivating an active alert if the condition remains out of range.

4. **Keep anomaly data separate**
   - `/api/groups/{group_id}/telemetry/anomalies` should remain a telemetry/analytics endpoint.
   - Do not feed anomaly rows into `alert_panel`.
   - Do not build a new anomaly widget in this fix; keep that as deferred follow-up.

---

## System-Wide Impact

- **Dashboard users** see fewer, meaningful alert cards with real titles/messages.
- **API consumers** gain an alerts endpoint; existing telemetry anomalies API remains unchanged.
- **Operators** get persistent dismissals instead of page-local suppression.
- **Developers** get clearer boundary between alert records and telemetry anomaly samples.
- **i18n** may need new strings for API-driven dismissal failure/success states or empty anomaly copy if a separate anomaly widget is added.

---

## High-Level Technical Design

This illustrates intended approach as directional guidance, not implementation specification.

```mermaid
flowchart LR
    ThresholdService[ThresholdService] --> AlertRepository[AlertRepository]
    AlertRepository --> AlertLog[(alert_log)]
    Dashboard[dashboard.py] --> AlertsAPI[GET /api/groups/{group_id}/alerts?status=active]
    AlertsAPI --> AlertRepository
    AlertsAPI --> Dashboard
    Dashboard --> AlertPanel[alert_panel]

    TelemetryRepo[TelemetryRepository.get_anomalies] --> AnomaliesAPI[/telemetry/anomalies]
    AnomaliesAPI -. future separate widget .-> AnomalySummary[Recent anomalies]
```

---

## Implementation Units

### U1. Add alert API schemas and router

**Goal:** Expose persisted alerts for a group and allow alert status updates.

**Requirements:** Active Alerts panel must receive structured alert records with stable IDs, titles, messages, severities, and timestamps.

**Dependencies:** None.

**Files:**

- Create `app/schemas/alerts.py`
- Create `app/api/alerts.py`
- Modify `app/main.py`
- Add/update `tests/integration/test_alerts_api.py`

**Approach:**

- Define `AlertResponse` with fields from `app/models/alert.py`: `id`, `group_id`, `greenhouse_id`, `zone_id`, `metric`, `severity`, `title`, `message`, `status`, `source`, `created_at`, `resolved_at`. Do not include `updated_at` unless a migration/model change is intentionally added later.
- Define a small update schema that allows only dashboard dismissal (`status="dismissed"`). Reject `active`, `resolved`, arbitrary strings, and unrelated fields for this endpoint.
- Add `GET /api/groups/{group_id}/alerts` with `status` filter only for this bug fix; default dashboard usage should request `status=active` with deterministic `created_at desc` ordering and a bounded limit.
- Add `PATCH /api/groups/{group_id}/alerts/{alert_id}` to dismiss an active alert and validate the alert belongs to the requested group before updating.
- Explicitly commit the database transaction after successful PATCH so dismissal persists across a new session and dashboard refresh.
- Register the router in `app/main.py` alongside existing API routers.
- Keep validation at API boundary; avoid broad repository attribute filtering exposure through the public endpoint.

**Patterns follow:**

- `app/api/greenhouses.py` for `APIRouter`, `Depends(get_db_session)`, `HTTPException`, and Pydantic response conversion.
- `app/repositories/alert_repository.py` for listing and updates.
- Existing Pydantic schema organization in `app/schemas/`.

**Test scenarios:**

- `GET /api/groups/{group_id}/alerts?status=active` returns only active alerts for that group with `title` and `message` present, ordered newest first and limited to the dashboard's bounded count.
- `GET /api/groups/{group_id}/alerts` rejects or ignores unsupported broad filters rather than exposing arbitrary repository attribute filters.
- `PATCH /api/groups/{group_id}/alerts/{alert_id}` changes status to `dismissed`, commits the transaction, and returns updated alert response.
- Reading the same alert in a new session after `PATCH` shows `status="dismissed"`.
- `PATCH` returns 404 when alert ID exists but belongs to a different group.
- Invalid status values such as `active`, `resolved`, or arbitrary strings return 422 or an explicit API validation error.
- If authentication/authorization is enabled for group APIs, unauthenticated or unauthorized callers cannot list or dismiss group alerts.

**Verification:** Alert API contract provides exactly the data `alert_panel` needs without fallback title/message behavior.

---

### U2. Update dashboard to load persisted active alerts

**Goal:** Stop rendering raw telemetry anomalies in the Active Alerts panel.

**Requirements:** Dashboard Active Alerts must display persisted active alerts, not raw anomaly rows.

**Dependencies:** U1.

**Files:**

- Modify `app/ui/pages/dashboard.py`
- Update `tests/unit/test_dashboard_view_models.py`
- Update `tests/integration/test_dashboard_data_flow.py`

**Approach:**

- Replace the dashboard fetch to `/api/groups/{group_id}/telemetry/anomalies` for the alert panel with `GET /api/groups/{group_id}/alerts?status=active`.
- Normalize API alert response fields for UI usage: set the alert display `timestamp` from `created_at` or update `alert_panel` to fall back to `created_at` when `timestamp` is absent.
- Update `alert_identity` to prefer persisted `id`; keep a defensive fallback only for non-persisted dictionaries used in tests.
- Build `group_data["active_alerts"]` from active persisted alert count.
- Keep existing page-local dismissal filtering in place until U3 replaces it with API-backed dismissal, or move all removal of `dismissed_alerts` into U3.

**Patterns follow:**

- Existing `api_client` use in `app/ui/pages/dashboard.py`.
- Existing pure view-model functions in `tests/unit/test_dashboard_view_models.py`.

**Test scenarios:**

- Raw anomaly-shaped dictionaries without title/message are no longer used to build Active Alerts count.
- Persisted alert-shaped dictionaries with IDs produce stable `alert_identity` values based on `id`.
- Group overview active alert count equals number of active persisted alerts loaded from alerts API.
- Empty alerts response displays "No active alerts" while telemetry readings still render greenhouse cards.
- Alert API loading or failure does not break greenhouse cards; the alert panel shows a localized inline error/retry state instead of pretending there are no alerts.
- Alert entries with `created_at` render equivalent timestamp data expected by `alert_panel`.

**Verification:** Dashboard no longer has a code path where `/telemetry/anomalies` rows are passed directly into `alert_panel`.

---

### U3. Persist dashboard alert dismissal

**Goal:** Make "Dismiss" and "Dismiss all" update alert status instead of hiding cards only in memory.

**Requirements:** Dismissal should survive refresh/reload and reduce active alert count.

**Dependencies:** U1, U2.

**Files:**

- Modify `app/ui/pages/dashboard.py`
- Update `tests/unit/test_dashboard_view_models.py` if dismissal helpers are extracted
- Add/update `tests/integration/test_alerts_api.py`

**Approach:**

- On single dismissal, call `PATCH /api/groups/{group_id}/alerts/{alert_id}` with `status="dismissed"`, then reload dashboard data.
- On dismiss all, patch each visible active alert ID. Keep the operation simple and scoped to displayed alerts.
- Remove page-local `dismissed_alerts` filtering after API-backed dismissal is in place.
- Keep user notifications localized and consistent with existing `Alert dismissed` and `All alerts dismissed` strings.
- If a patch fails, show a localized error notification and do not pretend the alert was dismissed.
- Disable dismiss buttons while requests are in flight; if dismiss all partially fails, reload server state and report a truthful partial result rather than "All alerts dismissed".
- Keep dismiss buttons keyboard-operable with localized aria labels that include the alert title when available; after dismissal, avoid leaving focus on a removed element.

**Patterns follow:**

- Existing NiceGUI async click handlers in `app/ui/pages/dashboard.py`.
- Existing notification usage in dashboard dismissal handlers.

**Test scenarios:**

- Single dismissal calls the alert update endpoint with the selected alert ID and reloads data.
- Dismiss all calls the update endpoint for each currently displayed active alert.
- A failed dismissal response leaves the alert visible after reload and shows an error notification path.
- Alerts without IDs are not sent to the persisted dismissal endpoint; this should be unreachable for Active Alerts after U2.

**Verification:** Refreshing dashboard after dismissal does not resurrect dismissed alerts because API query filters `status=active`.

---

### U4. Remove telemetry anomaly rows from Active Alerts

**Goal:** Keep raw anomaly analytics out of the operator alert panel.

**Requirements:** Raw anomaly samples must not create "Unknown Alert" cards.

**Dependencies:** U2.

**Files:**

- Modify `app/ui/pages/dashboard.py`
- Update `tests/integration/test_dashboard_data_flow.py`
- Update `tests/unit/test_dashboard_view_models.py`

**Approach:**

- Stop fetching anomalies on initial dashboard load unless another existing visible dashboard component still uses them.
- Do not build a new "Recent anomalies" widget in this fix; leave that in Deferred Follow-Up Work.
- Keep `/api/groups/{group_id}/telemetry/anomalies` unchanged for telemetry/API compatibility.

**Patterns follow:**

- Existing `section_card`/`empty_state` dashboard structure.
- Existing pure transformation tests in dashboard view-model test files.

**Test scenarios:**

- Dashboard with 100 raw anomaly rows and zero persisted active alerts shows zero Active Alerts.
- Removing anomaly fetch from the dashboard does not affect greenhouse cards, zone charts, or alert panel empty state.
- Existing telemetry anomalies API tests continue passing unchanged.

**Verification:** There is no remaining direct `alert_panel(anomalies, ...)` usage in dashboard.

---

### U5. Update translations and compile catalogs

**Goal:** Keep all new/changed user-facing strings localized in English and Ukrainian.

**Requirements:** Project convention requires all user-facing labels, descriptions, notifications, placeholders in `locales/`.

**Dependencies:** U2, U3, U4 if new anomaly UI strings are added.

**Files:**

- Modify `locales/messages.pot`
- Modify `locales/en/LC_MESSAGES/messages.po`
- Modify `locales/uk/LC_MESSAGES/messages.po`
- Generated compile output under `locales/*/LC_MESSAGES/messages.mo` if tracked by repo

**Approach:**

- Reuse existing strings where possible: `Active Alerts`, `No active alerts`, `Alert dismissed`, `All alerts dismissed`, `Dismiss alert`, `Dismiss all alerts`.
- Add translations only for genuinely new strings such as alert loading/failure copy, retry copy, or dismissal failure/partial-success copy.
- Run `pybabel compile locales` after `.po` changes per project instructions.

**Patterns follow:**

- `app.i18n.core._` render-time translation usage in NiceGUI components.
- Existing locale catalog format.

**Test scenarios:**

- Existing translation tests continue passing.
- New user-facing strings appear in both English and Ukrainian catalogs.
- Ukrainian dashboard view does not show untranslated English for new alert/anomaly text.

**Verification:** Compiled catalogs include new strings and dashboard renders without missing gettext keys.

---

### U6. Verify end-to-end dashboard behavior

**Goal:** Prove the fixed dashboard behavior through the running app, not only unit tests.

**Requirements:** UI change must be exercised in browser or documented if browser verification cannot run.

**Dependencies:** U1, U2, U3, U4, U5.

**Files:**

- Update or add relevant browser/manual verification notes only if repository already has a matching checklist location
- No new documentation file required unless user explicitly asks

**Approach:**

- Run targeted unit/integration tests for alert API and dashboard view-model behavior.
- Start/restart the Docker app after code changes per project memory and verify `/dashboard` through the app route.
- Seed or use existing data with at least one persisted active alert and repeated telemetry anomaly rows.
- Confirm dashboard shows persisted alert title/message, no `Unknown Alert`, and dismissal persists across refresh.
- Confirm empty state when no active alerts.

**Patterns follow:**

- Project instruction: for UI/frontend changes, use app in browser before reporting complete.
- Memory preference: test through Docker app and reload/restart Docker after code changes.

**Test scenarios:**

- Golden path: one active persisted alert appears with title, message, severity color, greenhouse/zone metadata, timestamp.
- Regression: 100 telemetry anomaly rows do not produce 100 Active Alerts cards.
- Dismissal: single dismiss removes alert and it stays gone after refresh.
- Dismiss all: multiple active alerts are dismissed and active count reaches zero.
- Localization: Ukrainian mode renders new labels/notifications in Ukrainian.

**Verification:** Browser screenshot or clear manual result confirms no "Unknown Alert" cards on dashboard.

---

## Risk Analysis

- **Status transition ambiguity:** Existing repository accepts any model attribute value. API schema should constrain this dashboard endpoint to `status="dismissed"` only.
- **Persistence bug risk:** `AlertRepository.update` flushes but does not commit; the API must commit successful PATCH requests and prove persistence with a new-session test.
- **Async UI failure handling:** Dismiss all may partially fail if one request fails. Keep behavior simple but truthful: disable controls while processing, reload server state, and report partial success/failure accurately.
- **Data availability:** If threshold evaluation is not currently running in dev, dashboard may show no active alerts until persisted alert data exists. Before rollout, verify dashboard-relevant threshold anomalies create persisted active alerts, or the UI could look falsely healthy.
- **Dismissal lifecycle:** Dismissing an alert must not be treated as resolving the underlying condition. Verify the threshold path can create or reactivate an active alert when telemetry remains out of range after dismissal.
- **API compatibility:** Existing anomalies endpoint remains unchanged to avoid breaking existing telemetry consumers.
- **Authorization:** New GET/PATCH endpoints must use the same auth/access-control pattern as existing group APIs if group-level authorization is present; tests should cover cross-group access and unauthorized access where the app supports it.

---

## Implementation Notes Deferred to Execution

- Exact schema field names can mirror model names unless existing API response conventions in touched files suggest otherwise during implementation.
- If compiled `.mo` files are not tracked or regenerated by existing workflow, follow current repository behavior observed during locale edits.
- If dashboard tests become easier with small pure helper functions for alert normalization, extract only what tests need; avoid broad dashboard refactor.

---

## Verification Strategy

1. Unit tests for dashboard pure helpers and alert identity/counting.
2. Integration tests for alerts API list/update behavior, including PATCH commit persistence in a new session.
3. Existing threshold service tests should remain green, proving alert creation still produces structured records.
4. Add or extend a threshold/alert integration test proving a dashboard-relevant out-of-range reading creates or recreates a persisted active alert when the condition remains out of range.
5. Existing telemetry API tests should remain green, proving anomaly endpoint compatibility.
6. Browser verification through Docker app for dashboard rendering, dismissal, empty state, alert load failure handling, and localization.

---

## Recommended Implementation Order

1. U1 creates the API contract and tests.
2. U2 switches dashboard reads to persisted active alerts.
3. U3 switches dismissal to persisted status updates.
4. U4 removes or separates raw anomaly presentation.
5. U5 updates translations and compiles catalogs.
6. U6 performs targeted automated and browser verification.
