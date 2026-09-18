# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A production-ready Django 5.2 LTS boilerplate configured for **QueryMaster**. The Python package is `querymaster/`.

## Commands

All operations run inside Docker containers via Makefile targets. There is no local venv workflow for running the app.

```bash
# Start dev environment
make dev.build && make dev.up.d

# Shell access
make dev.dcshell    # bash in django container
make dev.dshell     # django shell (with secrets sourced)
make dev.ipshell    # ipython shell

# Database
make dev.makemigrations
make dev.migrate
make dev.psql

# Run full test suite (spins up test containers, runs coverage)
make test

# Add/update packages: edit config/requirements/*.in, then:
make cr             # recompiles all requirements files via docker

# Linting (run locally via pre-commit)
pre-commit run --all-files
# Or individually:
ruff check .        # lint
ruff format .       # format
```

The `DJANGO_SETTINGS_MODULE` is set inside the Docker entrypoint per environment (`config.settings.dev`, `.test`, `.stage`, `.prod`).

## Architecture

### Settings structure

Settings are split by environment and concern, and imported additively:

- `config/settings/base.py` — shared config (DB, Celery, DRF, JWT, allauth, constance, logging)
- `config/settings/dev.py` — `DEBUG=True`, console email backend
- `config/settings/prod.py` — imports `base + brevo + s3 + sentry`, `DEBUG=False`
- `config/settings/brevo.py` — Anymail/Brevo email backend
- `config/settings/s3.py` — AWS S3 static/media storage
- `config/settings/sentry.py` / `constance.py` — Sentry and runtime config

### Secret management

All secrets come from **Infisical** via a sidecar container (`infisical-agent`). Secrets are written to `/secrets/app.env` and sourced before any Django command runs. The `.env` file at the repo root only contains Docker Compose bootstrap variables and Infisical credentials — not app secrets.

### App structure

```
querymaster/
  core/          — base models, paginations, logging middleware/handler, health check view
  users/         — custom User model (email-based, no username field)
config/
  settings/      — split settings files
  requirements/  — pinned deps per env (base/dev/stage/prod/test .in + .txt)
  nginx/         — nginx configs for stage/prod
  env/           — .env.example and .test env file
```

### API layout

Versioned under `api/v1/` inside each app:
- `querymaster/core/api/v1/` — health check endpoint
- `querymaster/users/api/v1/` — auth endpoints (register, login, logout, password, Google OAuth, delete account)

URL prefixes: `/api/v1/core/` and `/api/v1/users/`

Swagger UI at `/swagger/` (requires HTTP Basic auth).

### Authentication

JWT via `djangorestframework-simplejwt`. Managed through `dj-rest-auth` + `django-allauth`. Google social login supported. Email-based auth only — `username` field is absent from the `User` model. Email verification is mandatory. OTP flow is optional (controlled by `ENABLE_OTP` env var).

### Background tasks

Celery with Redis broker, `django-db` result backend. Beat scheduler uses `django_celery_beat` (DB-backed). Flower monitoring UI on port 5555.

### Caching and runtime config

Redis cache on DB index 1. `django-constance` with Redis backend on DB index 0 for runtime configuration (e.g., `MAX_LOG_BODY_CHARS_LIMIT` used by logging middleware).

### Logging

Every request/response is logged by `LoggingMiddleware` with UUID correlation, IP, method, path, status code, and a truncated response body. Custom `LoggingHandler` in `querymaster/core/logging/`.

## Coding Conventions (from Cursor rules)

- Always use class-based views (CBVs)
- Keep business logic in service modules; keep views thin
- Use Django ORM only; avoid raw SQL unless required for performance
- Use `select_related`/`prefetch_related` for related objects
- No Django signals
- Do not create new exception classes — use Django's built-in error handling
- Handle exceptions with try-except in business logic/views

## Adding a New Django App

1. Create app under `querymaster/`
2. Add to `CUSTOM_APPS` in `config/settings/base.py`
3. Create `api/v1/urls.py` and `api/v1/views.py` inside the app
4. Register URL prefix in `config/urls.py`
