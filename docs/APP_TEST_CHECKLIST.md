# App Test Checklist

Use this checklist when asked to test the whole Smart Greenhouse AI app. For production checks, verify through the deployed domain and nginx route, not localhost-only probes.

## Core access

- Login page accepts the configured admin credentials and redirects to the dashboard.
- Logout clears the session and returns to the login page.
- Protected pages redirect unauthenticated users to login.
- Language switch changes visible page text between English and Ukrainian after reload.

## Dashboard and diagnostics

- `/dashboard` loads without API or InfluxDB errors.
- Dashboard group and telemetry sections render the expected empty, demo, or live state.
- `/logs` loads persisted debug/error events without 401 errors.
- Log filters and refresh button update the displayed log list.

## Simulator and telemetry

- `/simulator` renders status, scenario cards, run configuration, mode selector, and start/stop controls.
- Scenario cards update the active scenario and show a notification.
- In MQTT control mode, Start Simulator shows the safety warning and does not start the internal simulator.
- In Internal simulator mode, Start Simulator starts telemetry generation, disables Start, enables Stop, and updates published-message counters.
- Stop Simulator stops telemetry generation and restores the stopped state.
- After simulator start, dashboard/control pages can display generated groups, greenhouses, zones, or fallback states as expected.

## Zones and plants

- `/zones` loads group/greenhouse scope selectors without API errors.
- Zone creation form validates required fields and creates a real MQTT zone when scope is valid.
- Plant batch form validates required fields and attaches a batch to a selected zone.
- `/plants` renders planned plant profile and batch sections without broken UI.

## Control panel

- `/control` loads group and greenhouse selectors without API errors.
- Greenhouse map renders selectable zones.
- Selecting a zone updates the drawer/context panel.
- Actuator controls show safe proposed actions before execution.
- In MQTT mode, approved actions publish to remote devices or show a clear error.
- In simulator mode, approved actions update simulator state.

## AI chat

- `/ai-chat` loads conversations and scope selectors without API errors.
- New conversation creates a clean thread.
- Sending a scoped question shows an assistant response or a clear failure message.
- Tool calls and proposed actions are visible when the assistant uses tools.
- Approval controls do not execute physical actions without explicit approval.

## RAG knowledge base

- `/rag` loads the documents list without API errors.
- Adding a text document validates title/content and indexes the document.
- Search returns relevant matches or a clear empty state.
- Reindex action completes or shows a clear error.
- File upload accepts supported text files and rejects invalid input cleanly.

## Settings

- `/settings` loads current chat model, embedding model, control mode, and model catalog.
- Control mode can switch between MQTT remote devices and Internal simulator, then persists after reload.
- Model catalog refresh/search/filter controls work without page errors.
- Selecting and saving a chat model persists after reload.

## Infrastructure and production services

- Docker Compose services are healthy: app, nginx, mosquitto, postgres, influxdb.
- Public HTTPS domain serves the app through nginx.
- App health endpoint is reachable through nginx where appropriate.
- Mosquitto is externally reachable only on the intended host/port and requires authentication.
- PostgreSQL and InfluxDB are not publicly exposed unless intentionally configured.
- Recent app/nginx/container logs contain no new 401, 500, 502, traceback, or unauthorized errors after the test run.

## Evidence to collect

- Routes tested and pass/fail result for each.
- Any browser console/page errors after clearing old logs and reloading.
- Container health summary.
- Relevant app/nginx log excerpts for failures.
- Notes for skipped checks, especially actions that would affect real devices or external services.
