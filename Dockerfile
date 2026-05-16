# ---- Stage 1: Build dependencies ----
FROM python:3.13-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /build
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

# Copy dependency manifests first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment
RUN uv sync --frozen --no-dev --no-install-project

# ---- Stage 2: Runtime ----
FROM python:3.13-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 appuser && useradd --uid 1000 --gid appuser --shell /bin/sh appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source
COPY app/ ./app/
COPY locales/ ./locales/
COPY migrations/ ./migrations/
COPY alembic.ini pyproject.toml uv.lock ./

# Switch to non-root user
USER appuser

EXPOSE 8080

# Health endpoint will be served by FastAPI; uvicorn starts the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
