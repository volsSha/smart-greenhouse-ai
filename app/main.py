"""FastAPI application with NiceGUI integration.

The application uses a lifespan context manager to initialize and shut
down infrastructure resources (DB engine, InfluxDB client). NiceGUI is
mounted via ``ui.run_with()`` at the entry point, not at import time,
so the FastAPI app remains testable without starting a server.

Usage::

    from app.main import app

    # For production, run with NiceGUI mounted:
    #   uvicorn app.main:asgi_app
    # or call the run() helper which invokes ui.run_with().
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.config import Settings
from app.dependencies import create_db_engine, create_influx_client
from app.services.influx_client import InfluxClient
from app.repositories.telemetry_repository import TelemetryRepository

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize and tear down infrastructure resources.

    Resources are stored on ``app.state`` so that dependency functions
    in ``app.dependencies`` can retrieve them.
    """
    settings = Settings()
    fastapi_app.state.settings = settings

    # --- Database ---
    db_engine: AsyncEngine = create_db_engine(settings)
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    fastapi_app.state.db_engine = db_engine
    fastapi_app.state.session_factory = session_factory
    logger.info("Database engine initialized")

    # --- InfluxDB ---
    influx_client = create_influx_client(settings)
    fastapi_app.state.influx_client = influx_client
    influx_wrapper = InfluxClient(
        url=settings.influxdb.url,
        token=settings.influxdb.token,
        org=settings.influxdb.org,
        bucket=settings.influxdb.bucket,
    )
    telemetry_repo = TelemetryRepository(influx_wrapper)
    fastapi_app.state.telemetry_repository = telemetry_repo
    logger.info("InfluxDB client initialized")

    # --- MQTT ---
    # MQTT client is created on-demand per connection (aiomqtt manages its
    # own lifecycle). We store settings so dependency can build clients.
    logger.info("MQTT configured (client created on-demand)")

    yield

    # --- Shutdown ---
    await db_engine.dispose()
    influx_wrapper.close()
    influx_client.close()
    logger.info("Infrastructure resources shut down")


# --- Create the FastAPI application ---
app = FastAPI(
    title="Smart Greenhouse Fleet Control",
    version="0.1.0",
    lifespan=lifespan,
)

# --- Register API routers ---
from app.api.health import router as health_router  # noqa: E402
from app.api.telemetry import router as telemetry_router  # noqa: E402
from app.api.groups import router as groups_router  # noqa: E402
from app.api.greenhouses import router as greenhouses_router  # noqa: E402
from app.api.devices import router as devices_router  # noqa: E402
from app.api.plants import router as plants_router  # noqa: E402
from app.api.commands import router as commands_router  # noqa: E402
from app.api.ai_chat import router as ai_chat_router  # noqa: E402
from app.api.rag import router as rag_router  # noqa: E402

app.include_router(health_router)
app.include_router(telemetry_router)
app.include_router(groups_router)
app.include_router(greenhouses_router)
app.include_router(devices_router)
app.include_router(plants_router)
app.include_router(commands_router)
app.include_router(ai_chat_router)
app.include_router(rag_router)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse("/dashboard")


# --- Register NiceGUI pages ---
# Importing the page modules registers their @ui.page() decorators
# with NiceGUI's internal router. The pages are not accessible until
# NiceGUI is mounted via ui.run_with() or ui.run().
from app.ui.pages import dashboard, settings, control, logs, ai_chat, rag  # noqa: E402, F401
from nicegui import ui  # noqa: E402

ui.run_with(
    app,
    title="Smart Greenhouse Fleet",
    storage_secret="",
)

logger.info("API routers and UI pages registered")


# Convenience alias for uvicorn:
#   uvicorn app.main:asgi_app
asgi_app = app
