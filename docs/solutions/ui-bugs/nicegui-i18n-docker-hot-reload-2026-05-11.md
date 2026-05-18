---
title: "NiceGUI i18n Language Switcher and Docker Hot Reload Fix"
date: 2026-05-11
category: "docs/solutions/ui-bugs/"
module: "NiceGUI / gettext / Docker"
problem_type: ui_bug
component: tooling
symptoms:
  - "Clicking the UA language switch reloaded the page but labels stayed English."
  - "Language switcher buttons showed flat/primary styling but never persisted the selected language."
  - "NiceGUI ui.select for language sent display labels instead of language codes."
  - "Ukrainian .po msgstr entries had English text prepended (doubled translations)."
  - "gettext returned msgids because /app/locales did not exist inside the container."
root_cause: wrong_api
resolution_type: code_fix
severity: medium
tags:
  - docker-compose
  - nicegui
  - gettext
  - i18n
  - hot-reload
  - language-switcher
last_updated: 2026-05-11
---

# NiceGUI i18n Language Switcher and Docker Hot Reload Fix

## Problem

The NiceGUI language switcher did not switch the UI language. Multiple causes compounded: the original two-button switcher passed the click event object as the language argument, the replacement `ui.select` emitted display labels instead of language codes, and several Ukrainian `.po` msgstr entries had the English original prepended (doubled translations). Separately, Docker dev environments had no hot reload for source or locale changes.

## Symptoms

- Browser click on `UA`/`EN` buttons caused a page reload with no visible label changes.
- `set_language_and_reload()` received the NiceGUI click event object, which `normalize_language()` mapped back to the default `"en"`.
- Replacing buttons with `ui.select` using `emit-value map-options` still failed: the select sent display labels like `"Ukrainian"` instead of code `"uk"`, `normalize_language()` rejected them, and the page fell back to English.
- Control page displayed doubled text: `"Propose, validate, approve, and execute actuator commands.Пропонуйте, перевіряйте..."`.
- Inside the container, `/app/locales` did not exist; `gettext.translation(..., fallback=True)` silently returned English msgids.

## What Didn't Work

- Two-button approach with `on_click=lambda lang=language: set_language_and_reload(lang)` — NiceGUI passes the click event as the first positional arg, shadowing the default.
- `ui.select` with `emit-value map-options` Quasar props — still emitted display labels because NiceGUI's Python-side event value uses the dict value, not the key.
- Setting `storage_secret=""` — empty string prevented NiceGUI user storage from persisting across page reloads.

## Solution

### 1. Language switcher: ui.select with label-to-code mapper

Replace the two-button switcher with a dropdown and a `_selected_language()` mapper that converts display labels back to language codes:

```python
# app/ui/components/language_switcher.py
from nicegui import ui
from app.i18n.core import _, get_current_language, normalize_language, set_language_and_reload

SUPPORTED_LANGUAGES = {"uk": _("Ukrainian"), "en": _("English")}

def _selected_language(value: object) -> str:
    if isinstance(value, str):
        labels = {_("Ukrainian"): "uk", _("English"): "en",
                   "Українська": "uk", "Англійська": "en"}
        return labels.get(value, normalize_language(value))
    return normalize_language(None)

def language_switcher() -> None:
    current_language = get_current_language()
    ui.select(
        list(SUPPORTED_LANGUAGES.values()),
        value=SUPPORTED_LANGUAGES[current_language],
        on_change=lambda event: set_language_and_reload(_selected_language(event.value)),
    ).props("dense outlined options-dense").classes("w-36")
```

### 2. Fix doubled Ukrainian translations

Several `msgstr` entries in `locales/uk/LC_MESSAGES/messages.po` had the English `msgid` text prepended. Fix by removing the English prefix:

```po
# BEFORE (broken — English prepended):
msgid "Propose, validate, approve, and execute actuator commands."
msgstr "Propose, validate, approve, and execute actuator commands."
"Пропонуйте, перевіряйте, затверджуйте та виконуйте команди виконавчих "
"пристроїв."

# AFTER (fixed — Ukrainian only):
msgid "Propose, validate, approve, and execute actuator commands."
msgstr ""
"Пропонуйте, перевіряйте, затверджуйте та виконуйте команди виконавчих "
"пристроїв."
```

After editing `.po` files, always recompile:

```bash
pybabel compile -d locales
```

### 3. Set a real storage_secret

NiceGUI user storage (`app.storage.user`) persists language preference across reloads. An empty `storage_secret` prevents persistence:

```python
# app/main.py
from app.config import get_settings

app_settings = get_settings()
ui.run_with(
    app,
    title="Smart Greenhouse Management",
    storage_secret=app_settings.app.app_secret or "smart-greenhouse-dev-secret",
)
```

### 4. Dev Docker with hot reload

Create `Dockerfile.dev` for local development with `uvicorn --reload`:

```dockerfile
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

Override in `compose.override.yml` to use the dev image and mount source volumes:

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

The production `Dockerfile` stays untouched (multi-stage, non-root, no reload).

### 5. Mount locale catalogs in dev

 gettext catalogs are loaded from `/app/locales` at runtime. Both the production image (`COPY locales/ ./locales/`) and the dev override (`./locales:/app/locales`) must provide them.

## Why This Works

- `_selected_language()` maps NiceGUI's display-label event values back to the canonical `"uk"`/`"en"` codes that `set_language_and_reload()` expects, handling both English and Ukrainian labels since the label itself changes with the active language.
- Removing English prefixes from `msgstr` entries eliminates the doubled-text rendering.
- A real `storage_secret` lets NiceGUI persist `app.storage.user` values (including the selected language) across page reloads via signed cookies.
- `Dockerfile.dev` with `--reload` watches `/app/app` and `/app/locales`, so source and translation edits are reflected live without container recreation.
- The dev override mounts the same directories for live-edit workflow while keeping the production Dockerfile lean.

## Prevention

- When using NiceGUI `ui.select` with internationalized labels, remember the `on_change` event value is the display label, not the dict key. Provide a reverse-mapping function.
- Always compile `.po` files with `pybabel compile -d locales` after editing, and verify with `gettext.translation(...).gettext()` in a Python REPL.
- Set a real `storage_secret` in `ui.run_with()` — an empty string breaks user-storage persistence.
- Keep dev Docker configuration in `Dockerfile.dev` and `compose.override.yml` so production images stay minimal.

## Related Issues

- `docs/solutions/ui-bugs/docker-compose-fastapi-nicegui-dashboard-launch-fix-2026-05-07.md` — initial Docker stack and NiceGUI mounting setup