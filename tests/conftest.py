"""Shared test fixtures for the Smart Greenhouse test suite."""

import pytest

from app.config import DatabaseSettings, InfluxDBSettings, MQTTSettings, OpenRouterSettings, Settings, AppSettings


@pytest.fixture()
def test_settings() -> Settings:
    """Return Settings with safe defaults for testing.

    Uses environment variables when set, otherwise falls back to defaults
    that work without external services.
    """
    return Settings(
        database=DatabaseSettings(
            host="localhost",
            port=5432,
            user="test_user",
            password="test_pass",
            db="test_db",
        ),
        influxdb=InfluxDBSettings(
            url="http://localhost:8086",
            token="test-token",
            org="test_org",
            bucket="test_bucket",
        ),
        mqtt=MQTTSettings(
            host="localhost",
            port=1883,
            username="test_user",
            password="test_pass",
        ),
        openrouter=OpenRouterSettings(
            api_key="test-key",
            model="test-model",
            base_url="https://openrouter.ai/api/v1",
        ),
        app=AppSettings(
            app_secret="test-secret",
            admin_username="admin",
            admin_password_hash="",
            debug=True,
        ),
    )
