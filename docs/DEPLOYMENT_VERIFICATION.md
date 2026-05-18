# Deployment verification

Use this checklist to prove the deployed Smart Greenhouse AI app works end-to-end after a production change.

## 1. Container and Compose state

Run checks from `/var/www/greenhouse` on the server.

- `docker compose -f deploy/production/compose.production.yml ps --all` shows these services running and healthy:
  - `greenhouse-prod-nginx`
  - `greenhouse-prod-app`
  - `greenhouse-prod-mosquitto`
  - `greenhouse-prod-postgres`
  - `greenhouse-prod-influxdb`
- `docker logs` for each container has no recent `Traceback`, `ERROR`, repeated restarts, or permission errors.
- The app image runs as `appuser`, and `/app/.nicegui` is writable by `appuser`.
- Database and InfluxDB containers keep existing named volumes; no reset, wipe, drop, or fresh migration command is used during verification.

## 2. Public HTTP and auth gates

- `https://greenhouse.volsh.dev/api/health/live` returns `200` without login.
- `https://greenhouse.volsh.dev/login` returns `200`.
- `https://greenhouse.volsh.dev/dashboard` redirects unauthenticated users to `/login`.
- Unauthenticated non-public APIs return `401`, for example:
  - `/api/groups`
  - `/api/debug-logs?limit=50&level=error`
  - `/api/simulator/status`
- After admin login, protected UI pages load without visible `401 Unauthorized` errors.

## 3. Internal app API calls

The NiceGUI UI calls FastAPI server-side. Verify authenticated in-container calls return `200`:

- `/api/groups`
- `/api/debug-logs?limit=1&level=error`
- `/api/simulator/status`
- `/api/ai/conversations`

If these return `401` while the page itself is logged in, check `API_BASE_URL` and session cookie handling first.

## 4. MQTT broker

- `greenhouse-prod-mosquitto` is healthy.
- Anonymous MQTT access is rejected.
- Authenticated publish/subscribe works through Docker networking on port `1883`.
- Authenticated publish/subscribe works through the host-exposed port `${MQTT_HOST_PORT:-11883}`.
- ACLs allow expected topics, especially `greenhouse-groups/#`.
- Hardware/Wokwi clients use the public host, external MQTT port, and a named broker user.

## 5. PostgreSQL and migrations

- `greenhouse-prod-postgres` health check passes.
- App startup does not log database connection failures.
- Current schema is at Alembic head using forward migrations only.
- Expected persisted records are present through app/API behavior, such as greenhouse groups, zones, plant batches, and AI conversations where applicable.

## 6. InfluxDB and telemetry

- `greenhouse-prod-influxdb` health check passes.
- App startup does not log InfluxDB connection failures.
- Dashboard telemetry requests complete after login.
- Recent MQTT telemetry published through Mosquitto appears in dashboard/API telemetry endpoints.

## 7. Browser feature verification

After login, verify these flows in a browser:

- Dashboard loads groups and telemetry cards without 401 or API error banners.
- Logs page loads error logs or an empty state without the previous `Error loading logs` message.
- Simulator page loads status; start/stop controls update state without API authorization errors.
- AI Chat page loads conversation list and scope selectors without 401 errors.
- Zone management/control pages load groups and dependent greenhouse/zone data.
- Language switcher still changes UI text between English and Ukrainian.
- Browser console has no repeated failed API calls, WebSocket failures, or uncaught exceptions.

## 8. Final evidence to collect

Record these proof points before declaring deployment healthy:

- Container status table with all production services healthy.
- HTTP status results for public health, login, unauthenticated dashboard redirect, and unauthenticated API 401.
- Authenticated internal API status results for groups, logs, simulator, and AI conversations.
- MQTT authenticated publish/subscribe result through the external port.
- Recent app/nginx/mosquitto logs showing no permission errors or unexpected 401s after login.
- Browser screenshots or notes for dashboard, logs, simulator, AI Chat, and zone/control flows.
