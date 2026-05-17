from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROD = ROOT / "deploy" / "production"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_production_compose_uses_repo_root_context_and_no_dev_mounts() -> None:
    compose = read(PROD / "compose.production.yml")

    assert "context: ../.." in compose
    assert "dockerfile: Dockerfile" in compose
    assert "./app:/app/app" not in compose
    assert "uvicorn app.main:app --reload" not in compose
    assert "../../infra/postgres/init:/docker-entrypoint-initdb.d:ro" in compose
    assert "./.env" in compose


def test_production_compose_defines_expected_services_and_private_dependencies() -> None:
    compose = read(PROD / "compose.production.yml")

    for service in ["mosquitto:", "postgres:", "influxdb:", "migrate:", "app:", "nginx:"]:
        assert service in compose

    assert "5432:" not in compose
    assert "8086:" not in compose
    assert "1883:" not in compose
    assert "9001:" not in compose
    assert "${NGINX_HTTP_PORT:-80}:80" in compose
    assert "${NGINX_HTTPS_PORT:-443}:443" in compose
    assert "APP_SECRET: ${APP_SECRET:?APP_SECRET is required}" in compose
    assert "ADMIN_USERNAME: ${ADMIN_USERNAME:?ADMIN_USERNAME is required}" in compose
    assert "ADMIN_PASSWORD_HASH: ${ADMIN_PASSWORD_HASH:?ADMIN_PASSWORD_HASH is required}" in compose


def test_migration_service_has_migration_assets_in_image() -> None:
    dockerfile = read(ROOT / "Dockerfile")
    compose = read(PROD / "compose.production.yml")

    assert "COPY migrations/ ./migrations/" in dockerfile
    assert "COPY alembic.ini pyproject.toml uv.lock ./" in dockerfile
    assert 'command: ["alembic", "upgrade", "head"]' in compose


def test_env_template_lists_required_names_without_real_secret_values() -> None:
    env = read(PROD / ".env.production.example")

    required_names = [
        "APP_SECRET",
        "ADMIN_USERNAME",
        "ADMIN_PASSWORD_HASH",
        "API_BASE_URL",
        "POSTGRES_PASSWORD",
        "INFLUX_TOKEN",
        "MQTT_PASSWORD",
        "OPENROUTER_API_KEY",
    ]
    for name in required_names:
        assert f"{name}=" in env

    assert "greenhouse.volsh.dev" in env
    assert "replace-with" in env


def test_nginx_gates_app_routes_and_leaves_liveness_public() -> None:
    nginx = read(PROD / "nginx" / "conf.d" / "greenhouse.conf")

    assert "server_name greenhouse.volsh.dev;" in nginx
    assert "listen 443 ssl" in nginx
    assert "return 301 https://$host$request_uri;" in nginx
    assert "location = /api/health/live" in nginx
    assert "auth_basic" not in nginx
    assert "auth_basic_user_file" not in nginx
    assert "proxy_buffering off;" in nginx


def test_mosquitto_production_config_requires_auth_and_acl() -> None:
    conf = read(PROD / "mosquitto" / "mosquitto.conf")
    acl = read(PROD / "mosquitto" / "acl.conf")

    assert "allow_anonymous false" in conf
    assert "password_file /mosquitto/config/passwords" in conf
    assert "acl_file /mosquitto/config/acl.conf" in conf
    assert "user app" in acl
    assert "topic readwrite greenhouse-groups/#" in acl


def test_runbook_documents_safety_gates() -> None:
    runbook = read(PROD / "README.md")

    for phrase in [
        "Do not commit or sync",
        "app-level admin login",
        "allow_anonymous false",
        "empty volumes or restores existing",
        "Do not run reset/fresh/wipe/drop commands",
        "Ask before removing containers or volumes",
        "Future project routes",
    ]:
        assert phrase in runbook


def test_operations_links_production_runbook() -> None:
    operations = read(ROOT / "docs" / "OPERATIONS.md")

    assert "deploy/production/README.md" in operations
    assert "greenhouse.volsh.dev" in operations
