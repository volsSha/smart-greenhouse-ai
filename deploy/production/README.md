# Production deployment

This directory contains the Docker-only production deployment for `greenhouse.volsh.dev`. Run commands from the repository root on the server (`/var/www/greenhouse`) with `-f deploy/production/compose.production.yml` so build context and mounted config paths resolve correctly.

## Files

- `compose.production.yml` — production app, migration, PostgreSQL, InfluxDB, Mosquitto, and nginx services
- `.env.production.example` — placeholder-only template for the server `.env`
- `nginx/` — Docker nginx config for `greenhouse.volsh.dev`
- `mosquitto/` — production broker config with anonymous access disabled

## Server-only secrets

Create these files only on the server. Do not commit or sync them from a workstation.

- `.env`
- `deploy/production/secrets/nginx.htpasswd`
- `deploy/production/secrets/mosquitto_passwords`
- TLS private keys under `deploy/production/certs/`

Use restrictive permissions for secret files, for example owner-readable only for `.env` and secret material. Never pass secret values on command lines, paste them into logs, or print them for verification. Check only whether required variable names are present.

## Required environment variables

Start from `.env.production.example` and replace every placeholder on the server. Production requires non-empty values for:

- `APP_SECRET`, `API_BASE_URL`, `DEBUG`
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `INFLUX_URL`, `INFLUX_PASSWORD`, `INFLUX_TOKEN`, `INFLUX_ORG`, `INFLUX_BUCKET`
- `MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD`, `MQTT_PASSWORD_FILE`
- `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`, `OPENROUTER_EMBEDDING_MODEL`, `OPENROUTER_EMBEDDING_DIMENSION`
- `NGINX_HTTP_PORT`, `NGINX_HTTPS_PORT`, `NGINX_CERTS_DIR`, `NGINX_HTPASSWD_FILE`

## TLS and access gate

Docker nginx is the intended public entrypoint for `greenhouse.volsh.dev`. Before starting nginx, inspect the server for any existing listener on ports 80/443. If a shared Docker-managed proxy already owns TLS for the host, get explicit approval before integrating behind it. Do not replace or stop an existing proxy without approval.

Default production access is gated at nginx with Basic Auth. Keep only `/api/health/live` public for uptime checks; all other UI and API routes should require authentication unless app-level auth replaces this temporary gate. If route-level gating is ever used instead, enumerate FastAPI routes and verify every non-public `/api/*` route is protected.

Generate `deploy/production/secrets/nginx.htpasswd` on the server, mount it read-only, keep it out of sync/git, and rotate or remove it when app-level authentication is available.

## Mosquitto credentials

Production Mosquitto uses `allow_anonymous false` and a server-side password file. Generate `deploy/production/secrets/mosquitto_passwords` on the server with users that match `mosquitto/acl.conf` (`app`, `simulator`, and `wokwi` as needed). The app uses `MQTT_USERNAME` and `MQTT_PASSWORD` from `.env`; do not commit broker passwords.

Do not publish MQTT ports on the host unless explicitly approved.

## Data and migration gate

Before the first production start, decide whether this deployment starts with empty volumes or restores existing PostgreSQL/InfluxDB data.

If existing data matters:

1. Create or verify restorable PostgreSQL and InfluxDB backups/snapshots.
2. Restore/import into the Docker-managed volumes.
3. Verify expected greenhouse groups, zones, telemetry, and documents before public cutover.

Before every production migration:

1. Build and validate the new image/compose config.
2. Create or verify a restorable database backup/snapshot.
3. Confirm the rollback path is known after `alembic upgrade head`.
4. Run only forward migrations. Do not run reset/fresh/wipe/drop commands.

## Remote sync safety

Prefer deploying from a known clean git commit on the server. If syncing files to `/var/www/greenhouse`, use an allowlist for required repo artifacts and explicitly exclude:

- `.env*` except the server-created production `.env`
- `.git/`, `.claude/`, `.agents/`, `.venv/`, `temp/`, caches, logs, and test output
- local secret files, editor files, and dev-only artifacts

## Deployment flow

1. Inspect remote Docker state, running containers, volumes, and ports before changing anything.
2. Prepare `.env`, TLS cert files, nginx htpasswd, and Mosquitto password file on the server.
3. Validate the production Compose file from repo root.
4. Start dependencies.
5. Run `alembic upgrade head` through the `migrate` service.
6. Start the app and nginx.
7. Verify `https://greenhouse.volsh.dev/api/health/live` is public.
8. Verify `/api/health/ready`, `/dashboard`, `/ai-chat`, `/logs`, and other app routes are gated.
9. Verify the app readiness and UI flows from `docs/OPERATIONS.md`.

Ask before removing containers or volumes, replacing existing reverse proxy behavior, exposing MQTT publicly, or skipping backups before migration.

## Future project routes

Add future project routes as new files under `nginx/conf.d/`. Keep each project in its own server block and avoid catch-all routing to the greenhouse app.
