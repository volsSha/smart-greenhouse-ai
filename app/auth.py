"""Admin authentication helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from urllib.parse import parse_qs

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from app.config import Settings

_COOKIE_SECURITY_OPTIONS = {"httponly": True, "samesite": "lax"}

AUTH_COOKIE_NAME = "greenhouse_admin_session"
_PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
_DEFAULT_ITERATIONS = 600_000

PUBLIC_PATHS = {
    "/api/health/live",
    "/login",
    "/favicon.ico",
}
PUBLIC_PATH_PREFIXES = (
    "/_nicegui/",
    "/_nicegui_ws",
    "/static/",
)


def hash_admin_password(password: str, *, salt: str | None = None, iterations: int = _DEFAULT_ITERATIONS) -> str:
    salt = salt or secrets.token_urlsafe(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    encoded_digest = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return f"{_PASSWORD_HASH_ALGORITHM}:{iterations}:{salt}:{encoded_digest}"


def verify_admin_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, expected_digest = password_hash.split(":", 3)
        iterations = int(iterations_text)
    except ValueError:
        return False

    if algorithm != _PASSWORD_HASH_ALGORITHM:
        return False

    actual_hash = hash_admin_password(password, salt=salt, iterations=iterations)
    return hmac.compare_digest(actual_hash, password_hash)


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES)


def is_auth_enabled(settings: Settings) -> bool:
    return bool(settings.app.admin_password_hash)


def is_authenticated(request: Request, settings: Settings) -> bool:
    token = request.cookies.get(AUTH_COOKIE_NAME)
    return is_session_token_valid(token, settings)


def is_session_token_valid(token: str | None, settings: Settings) -> bool:
    if not token or not settings.app.app_secret:
        return False

    return hmac.compare_digest(token, session_token(settings))


def login_response(settings: Settings) -> RedirectResponse:
    response = RedirectResponse("/dashboard", status_code=303)
    response.set_cookie(
        AUTH_COOKIE_NAME,
        session_token(settings),
        **_cookie_options(settings),
    )
    return response


def logout_response(settings: Settings) -> RedirectResponse:
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(AUTH_COOKIE_NAME, **_cookie_options(settings))
    return response


async def login_get() -> HTMLResponse:
    return _login_page()


async def login_post(request: Request) -> Response:
    settings = settings_from_request(request)
    form = parse_qs((await request.body()).decode())
    username = form.get("username", [""])[0]
    password = form.get("password", [""])[0]

    if not settings.app.admin_password_hash:
        return _login_page("Admin password hash is not configured.", status_code=503)

    if username != settings.app.admin_username or not verify_admin_password(password, settings.app.admin_password_hash):
        return _login_page("Invalid username or password.", status_code=401)

    return login_response(settings)


async def logout_get(request: Request) -> RedirectResponse:
    return logout_response(settings_from_request(request))


def unauthenticated_response(request: Request) -> Response:
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Authentication required"}, status_code=401)
    return RedirectResponse("/login", status_code=303)


def settings_from_request(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if isinstance(settings, Settings):
        return settings
    return Settings()


def _cookie_options(settings: Settings) -> dict[str, bool | str]:
    return {**_COOKIE_SECURITY_OPTIONS, "secure": not settings.app.debug}


def session_token(settings: Settings) -> str:
    signature = hmac.new(settings.app.app_secret.encode(), b"admin", hashlib.sha256).hexdigest()
    return f"admin.{signature}"


def _login_page(error: str = "", *, status_code: int = 200) -> HTMLResponse:
    error_html = f'<p class="error">{error}</p>' if error else ""
    return HTMLResponse(
        f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Smart Greenhouse Login</title>
  <style>
    body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; font-family: system-ui, sans-serif; background: #f3f7f2; color: #17351f; }}
    main {{ width: min(100% - 2rem, 24rem); padding: 2rem; border-radius: 1.25rem; background: white; box-shadow: 0 1.25rem 3rem rgb(23 53 31 / 12%); }}
    h1 {{ margin: 0 0 .5rem; font-size: 1.5rem; }}
    p {{ margin: 0 0 1.5rem; color: #56705c; }}
    label {{ display: grid; gap: .35rem; margin-bottom: 1rem; font-weight: 600; }}
    input {{ padding: .75rem .9rem; border: 1px solid #cdd9cf; border-radius: .75rem; font: inherit; }}
    button {{ width: 100%; padding: .8rem 1rem; border: 0; border-radius: .75rem; background: #1f7a3f; color: white; font: inherit; font-weight: 700; cursor: pointer; }}
    .error {{ padding: .75rem; border-radius: .75rem; background: #fee2e2; color: #991b1b; }}
  </style>
</head>
<body>
  <main>
    <h1>Smart Greenhouse</h1>
    <p>Sign in to manage the fleet.</p>
    {error_html}
    <form method="post" action="/login">
      <label>Username <input name="username" autocomplete="username" required autofocus></label>
      <label>Password <input name="password" type="password" autocomplete="current-password" required></label>
      <button type="submit">Sign in</button>
    </form>
  </main>
</body>
</html>
""",
        status_code=status_code,
    )
