"""Tests for app.config — settings loading and validation."""

import os
from unittest.mock import patch

import pytest

from app.config import (
    AppSettings,
    DatabaseSettings,
    InfluxDBSettings,
    MQTTSettings,
    OpenRouterSettings,
    Settings,
    get_settings,
)


class TestDatabaseSettings:
    """Tests for DatabaseSettings."""

    def test_default_values(self) -> None:
        """DatabaseSettings uses localhost defaults when no env vars are set."""
        with patch.dict(os.environ, {}, clear=True):
            settings = DatabaseSettings()
        assert settings.host == "localhost"
        assert settings.port == 5432
        assert settings.user == "greenhouse_user"
        assert settings.db == "greenhouse_db"

    def test_env_override(self) -> None:
        """DatabaseSettings reads POSTGRES_ prefixed env vars."""
        env = {
            "POSTGRES_HOST": "db.example.com",
            "POSTGRES_PORT": "5433",
            "POSTGRES_USER": "admin",
            "POSTGRES_PASSWORD": "secret",
            "POSTGRES_DB": "production",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = DatabaseSettings()
        assert settings.host == "db.example.com"
        assert settings.port == 5433
        assert settings.user == "admin"
        assert settings.password == "secret"
        assert settings.db == "production"

    def test_url_property(self) -> None:
        """DatabaseSettings.url builds a valid asyncpg connection string."""
        settings = DatabaseSettings(
            host="dbhost", port=5432, user="me", password="pw", db="mydb"
        )
        assert settings.url == "postgresql+asyncpg://me:pw@dbhost:5432/mydb"


class TestInfluxDBSettings:
    """Tests for InfluxDBSettings."""

    def test_default_values(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = InfluxDBSettings()
        assert settings.url == "http://localhost:8086"
        assert settings.org == "greenhouse_org"
        assert settings.bucket == "microclimate"

    def test_env_override(self) -> None:
        env = {
            "INFLUX_URL": "http://influx:8086",
            "INFLUX_TOKEN": "my-token",
            "INFLUX_ORG": "my-org",
            "INFLUX_BUCKET": "my-bucket",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = InfluxDBSettings()
        assert settings.url == "http://influx:8086"
        assert settings.token == "my-token"
        assert settings.org == "my-org"
        assert settings.bucket == "my-bucket"


class TestMQTTSettings:
    """Tests for MQTTSettings."""

    def test_default_values(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = MQTTSettings()
        assert settings.host == "localhost"
        assert settings.port == 1883
        assert settings.username == ""
        assert settings.password == ""

    def test_broker_url_without_credentials(self) -> None:
        settings = MQTTSettings(host="mqtt.local", port=1883)
        assert settings.broker_url == "mqtt://mqtt.local:1883"

    def test_broker_url_with_credentials(self) -> None:
        settings = MQTTSettings(
            host="mqtt.local", port=1883, username="user", password="pass"
        )
        assert settings.broker_url == "mqtt://user:pass@mqtt.local:1883"


class TestOpenRouterSettings:
    """Tests for OpenRouterSettings."""

    def test_default_values(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = OpenRouterSettings()
        assert settings.api_key == ""
        assert settings.model == "anthropic/claude-sonnet-4"
        assert settings.base_url == "https://openrouter.ai/api/v1"
        assert settings.embedding_model == "openai/text-embedding-3-small"
        assert settings.embedding_dimension == 1536

    def test_embedding_model_from_env(self) -> None:
        """Embedding model and dimension can be configured via env vars."""
        env = {
            "OPENROUTER_EMBEDDING_MODEL": "openai/text-embedding-3-large",
            "OPENROUTER_EMBEDDING_DIMENSION": "3072",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = OpenRouterSettings()
        assert settings.embedding_model == "openai/text-embedding-3-large"
        assert settings.embedding_dimension == 3072


class TestAppSettings:
    """Tests for AppSettings."""

    def test_default_values(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = AppSettings()
        assert settings.app_secret == ""
        assert settings.debug is False

    def test_debug_from_env(self) -> None:
        with patch.dict(os.environ, {"DEBUG": "true"}, clear=True):
            settings = AppSettings()
        assert settings.debug is True


class TestSettings:
    """Tests for the root Settings composition."""

    def test_composed_defaults(self) -> None:
        """Settings composes all sub-settings with their defaults."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
        assert isinstance(settings.database, DatabaseSettings)
        assert isinstance(settings.influxdb, InfluxDBSettings)
        assert isinstance(settings.mqtt, MQTTSettings)
        assert isinstance(settings.openrouter, OpenRouterSettings)
        assert isinstance(settings.app, AppSettings)

    def test_nested_env_override(self) -> None:
        """Settings reads nested values via DATABASE__HOST style env vars."""
        env = {
            "DATABASE__HOST": "override-host",
            "APP__DEBUG": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
        assert settings.database.host == "override-host"
        assert settings.app.debug is True

    def test_explicit_construction(self, test_settings: Settings) -> None:
        """Settings can be constructed with explicit sub-settings for testing."""
        assert test_settings.database.host == "localhost"
        assert test_settings.influxdb.token == "test-token"
        assert test_settings.mqtt.username == "test_user"
        assert test_settings.openrouter.api_key == "test-key"
        assert test_settings.app.debug is True

    def test_get_settings_returns_settings(self) -> None:
        """get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)
