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
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from app.auth import is_auth_enabled, is_authenticated, is_public_path, login_get, login_post, logout_get, settings_from_request, unauthenticated_response
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.config import Settings, get_settings
from app.dependencies import create_db_engine, create_influx_client
from app.services.influx_client import InfluxClient
from app.repositories.debug_log_repository import create_debug_log_best_effort
from app.repositories.telemetry_repository import TelemetryRepository
from app.services.mqtt_runtime import MQTTRuntime
from app.api.simulator import stop_simulator_task
from app.services.telemetry_ingestion import TelemetryIngestion

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
    telemetry_ingestion = TelemetryIngestion(influx_client=influx_wrapper)
    mqtt_runtime = MQTTRuntime(settings.mqtt, telemetry_ingestion)
    fastapi_app.state.mqtt_runtime = mqtt_runtime
    await mqtt_runtime.start()
    logger.info("MQTT telemetry runtime started")

    yield

    # --- Shutdown ---
    await stop_simulator_task(fastapi_app.state)
    await mqtt_runtime.stop()
    await db_engine.dispose()
    influx_wrapper.close()
    influx_client.close()
    logger.info("Infrastructure resources shut down")


# --- Create the FastAPI application ---
app = FastAPI(
    title="Smart Greenhouse Management",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def admin_auth_middleware(request: Request, call_next):
    settings = settings_from_request(request)
    if is_auth_enabled(settings) and not is_public_path(request.url.path) and not is_authenticated(request, settings):
        return unauthenticated_response(request)
    return await call_next(request)


async def _write_request_log(
    request: Request,
    *,
    level: str,
    event_type: str,
    message: str,
    status_code: int | None,
    duration_ms: float,
    error: Exception | None = None,
) -> None:
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        logger.warning("Debug log skipped because database session factory is unavailable")
        return

    await create_debug_log_best_effort(
        session_factory,
        level=level,
        event_type=event_type,
        component="api",
        message=message,
        path=request.url.path,
        method=request.method,
        status_code=status_code,
        duration_ms=duration_ms,
        request_id=request.headers.get("x-request-id") or str(uuid.uuid4()),
        error_type=type(error).__name__ if error else None,
        stack_trace="".join(traceback.format_exception(error)) if error else None,
        metadata={
            "query_params": dict(request.query_params),
            "client_host": request.client.host if request.client else None,
        },
    )


@app.middleware("http")
async def debug_log_middleware(request: Request, call_next):
    started_at = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = (time.perf_counter() - started_at) * 1000
        await _write_request_log(
            request,
            level="error",
            event_type="unhandled_exception",
            message=str(exc),
            status_code=500,
            duration_ms=duration_ms,
            error=exc,
        )
        raise

    duration_ms = (time.perf_counter() - started_at) * 1000
    if response.status_code >= 500:
        await _write_request_log(
            request,
            level="error",
            event_type="http_5xx",
            message=f"HTTP {response.status_code}",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
    return response


# --- Register API routers ---
from app.api.health import router as health_router  # noqa: E402
from app.api.telemetry import router as telemetry_router  # noqa: E402
from app.api.groups import router as groups_router  # noqa: E402
from app.api.greenhouses import router as greenhouses_router  # noqa: E402
from app.api.devices import router as devices_router  # noqa: E402
from app.api.plants import router as plants_router  # noqa: E402
from app.api.commands import router as commands_router  # noqa: E402
from app.api.ai_chat import router as ai_chat_router  # noqa: E402
from app.api.debug_logs import router as debug_logs_router  # noqa: E402
from app.api.rag import router as rag_router  # noqa: E402
from app.api.simulator import router as simulator_router  # noqa: E402
from app.api.simulator_state import router as simulator_state_router  # noqa: E402
from app.api.mqtt_status import router as mqtt_status_router  # noqa: E402
from app.api.settings import router as settings_router  # noqa: E402

app.include_router(health_router)
app.include_router(telemetry_router)
app.include_router(groups_router)
app.include_router(greenhouses_router)
app.include_router(devices_router)
app.include_router(plants_router)
app.include_router(commands_router)
app.include_router(ai_chat_router)
app.include_router(debug_logs_router)
app.include_router(rag_router)
app.include_router(simulator_router)
app.include_router(simulator_state_router)
app.include_router(mqtt_status_router)
app.include_router(settings_router)

app.add_api_route("/login", login_get, methods=["GET"], include_in_schema=False)
app.add_api_route("/login", login_post, methods=["POST"], include_in_schema=False)
app.add_api_route("/logout", logout_get, methods=["GET"], include_in_schema=False)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse("/dashboard")


# --- Register NiceGUI pages ---
# Importing the page modules registers their @ui.page() decorators
# with NiceGUI's internal router. The pages are not accessible until
# NiceGUI is mounted via ui.run_with() or ui.run().
from app.ui.pages import dashboard, settings as settings_page, control, logs, ai_chat, rag, simulator, plants, zone_management  # noqa: E402, F401
from nicegui import ui  # noqa: E402


def _load_theme_css() -> None:
    css_path = Path(__file__).parent / "ui" / "static" / "theme.css"
    try:
        ui.add_css(css_path.read_text(), shared=True)
    except FileNotFoundError:
        logger.warning("theme.css not found at %s", css_path)


_load_theme_css()
app_settings = get_settings()

ui.run_with(
    app,
    title="Smart Greenhouse Management",
    storage_secret=app_settings.app.app_secret or "smart-greenhouse-dev-secret",
)

logger.info("API routers and UI pages registered")


# Convenience alias for uvicorn:
#   uvicorn app.main:asgi_app
asgi_app = app
