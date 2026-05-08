"""Application configuration using pydantic-settings with nested models."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL connection settings."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", extra="ignore")

    host: str = "localhost"
    port: int = 5432
    user: str = "greenhouse_user"
    password: str = ""
    db: str = "greenhouse_db"

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class InfluxDBSettings(BaseSettings):
    """InfluxDB connection settings."""

    model_config = SettingsConfigDict(env_prefix="INFLUX_", extra="ignore")

    url: str = "http://localhost:8086"
    token: str = ""
    org: str = "greenhouse_org"
    bucket: str = "microclimate"


class MQTTSettings(BaseSettings):
    """MQTT broker connection settings."""

    model_config = SettingsConfigDict(env_prefix="MQTT_", extra="ignore")

    host: str = "localhost"
    port: int = 1883
    username: str = ""
    password: str = ""

    @property
    def broker_url(self) -> str:
        if self.username and self.password:
            return f"mqtt://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"mqtt://{self.host}:{self.port}"


class OpenRouterSettings(BaseSettings):
    """OpenRouter LLM provider settings."""

    model_config = SettingsConfigDict(env_prefix="OPENROUTER_", extra="ignore")

    api_key: str = ""
    model: str = "anthropic/claude-sonnet-4"
    base_url: str = "https://openrouter.ai/api/v1"


class AppSettings(BaseSettings):
    """General application settings."""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    app_secret: str = ""
    debug: bool = False
    api_base_url: str = "http://127.0.0.1:8080"


class Settings(BaseSettings):
    """Root application settings that compose all sub-settings.

    Loads values from environment variables and .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    influxdb: InfluxDBSettings = Field(default_factory=InfluxDBSettings)
    mqtt: MQTTSettings = Field(default_factory=MQTTSettings)
    openrouter: OpenRouterSettings = Field(default_factory=OpenRouterSettings)
    app: AppSettings = Field(default_factory=AppSettings)


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
