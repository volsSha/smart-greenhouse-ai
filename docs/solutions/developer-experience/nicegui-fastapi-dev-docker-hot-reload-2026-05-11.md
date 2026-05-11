---
title: "NiceGUI FastAPI Dev Docker Hot Reload Setup"
date: 2026-05-11
category: "docs/solutions/developer-experience/"
module: "Docker / NiceGUI / FastAPI"
problem_type: developer_experience
component: development_workflow
severity: medium
applies_when:
  - "Developing NiceGUI or FastAPI changes in a Docker-based dev environment"
  - "Editing .po translation files and wanting live preview without container restarts"
tags:
  - docker
  - nicegui
  - fastapi
  - hot-reload
  - dev-environment
---

# NiceGUI FastAPI Dev Docker Hot Reload Setup

## Context

The production Dockerfile is a multi-stage build optimized for size and security (non-root user, minimal layers, no dev dependencies). This means source edits require `docker compose up -d --build` to see changes — unacceptable for local development where you want instant feedback on UI or translation edits.

## Guidance

Create a separate `Dockerfile.dev` that optimizes for developer experience:

```dockerfile
# Dockerfile.dev — development only, NOT for production
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev curl && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY app/ ./app/
COPY locales/ ./locales/

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080",
     "--reload", "--reload-dir", "/app/app", "--reload-dir", "/app/locales"]
```

Key differences from production `Dockerfile`:

| Aspect | Production (`Dockerfile`) | Dev (`Dockerfile.dev`) |
|--------|--------------------------|------------------------|
| Stages | Multi-stage (builder + runtime) | Single stage |
| Dev deps | Not installed | Installed by `uv sync` |
| User | Non-root `appuser` | Root (simpler for dev) |
| Reload | None | `--reload` with watch dirs |
| Source mount | Read-only `./app:/app/app:ro` | Read-write `./app:/app/app` |

Wire it in `compose.override.yml` (auto-loaded by Docker Compose for local dev):

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - ./app:/app/app
      - ./locales:/app/locales
      - ./tests:/app/tests
    environment:
      DEBUG: "true"
```

The production `docker-compose.yml` continues using `dockerfile: Dockerfile` — so CI and production builds are unaffected.

## Why This Matters

Without hot reload, every UI tweak or translation edit requires a 30+ second container rebuild. With `--reload`, uvicorn detects file changes in mounted volumes and restarts the worker process in 1-2 seconds. This brings the Docker dev experience close to local `uvicorn --reload`.

The `--reload-dir /app/locales` flag ensures that compiled `.mo` files changed by `pybabel compile -d locales` on the host trigger a live reload in the container. Note: only the compiled `.mo` files need to change — uvicorn watches the directory for any file modification, and gettext loads the `.mo` on each translation call when `lru_cache` is not yet populated.

## When to Apply

- When setting up Docker-based local development for a NiceGUI/FastAPI project.
- When adding i18n support and needing live translation preview.
- When onboarding new developers who will work on UI changes in Docker.

## Examples

Starting dev environment:

```bash
# Build and start dev container (first time or after dependency changes)
docker compose up -d --build app

# Subsequent starts — source changes are picked up by --reload
docker compose up -d

# After editing .po files, compile and the container auto-reloads
pybabel compile -d locales
# No rebuild needed — --reload-dir picks up the .mo change
```

Switching back to production image for testing:

```bash
# Temporarily use production build
docker compose up -d --build --force-recreate app
# This uses Dockerfile (not Dockerfile.dev) because compose.override.yml
# overrides dockerfile. Comment out the dockerfile override first.
```

## Related

- `docs/solutions/ui-bugs/nicegui-i18n-docker-hot-reload-2026-05-11.md` — language switcher fix and locale mounting
- `docs/solutions/ui-bugs/docker-compose-fastapi-nicegui-dashboard-launch-fix-2026-05-07.md` — initial Docker stack setup