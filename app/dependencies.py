"""FastAPI dependency providers for lifespan-managed resources.

Dependencies are initialized during app startup and stored on the
application state (request.app.state). Each dependency function
retrieves its resource from state, making them testable via
dependency overrides.
"""

from collections.abc import AsyncGenerator

import aiomqtt
from fastapi import Request
from influxdb_client import InfluxDBClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings
from app.services.command_publisher import CommandPublisher


def get_settings() -> Settings:
    """Return the application settings instance.

    In production, this reads from environment variables and .env.
    Tests can override by providing a Settings directly.
    """
    return Settings()


def create_db_engine(settings: Settings) -> AsyncEngine:
    """Create an async SQLAlchemy engine from settings."""
    return create_async_engine(
        settings.database.url,
        echo=settings.app.debug,
        pool_size=5,
        max_overflow=10,
    )


def create_influx_client(settings: Settings) -> InfluxDBClient:
    """Create an InfluxDB client from settings."""
    return InfluxDBClient(
        url=settings.influxdb.url,
        token=settings.influxdb.token,
        org=settings.influxdb.org,
    )


def create_mqtt_client(settings: Settings) -> aiomqtt.Client:
    """Create an MQTT client from settings.

    This returns an aiomqtt.Client that must be used as an async context
    manager. The lifespan stores the settings so consumers can connect
    as needed.
    """
    return aiomqtt.Client(
        hostname=settings.mqtt.host,
        port=settings.mqtt.port,
        username=settings.mqtt.username or None,
        password=settings.mqtt.password or None,
    )


async def get_db_engine(request: Request) -> AsyncGenerator[AsyncEngine, None]:
    """Yield the async database engine from app state."""
    engine: AsyncEngine = request.app.state.db_engine
    yield engine


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        yield session


async def get_influx_client(request: Request) -> AsyncGenerator[InfluxDBClient, None]:
    """Yield the InfluxDB client from app state."""
    client: InfluxDBClient = request.app.state.influx_client
    yield client


async def get_mqtt_client(request: Request) -> AsyncGenerator[aiomqtt.Client, None]:
    """Yield the MQTT client from app state."""
    settings: Settings = request.app.state.settings
    yield create_mqtt_client(settings)


async def get_command_publisher(request: Request) -> AsyncGenerator[CommandPublisher, None]:
    """Yield the MQTT command publisher built from app settings."""
    settings: Settings = request.app.state.settings
    yield CommandPublisher(settings.mqtt)
