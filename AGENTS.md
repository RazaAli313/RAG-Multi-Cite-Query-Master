# AGENTS.md

This file provides guidance for coding agents working in this repository.

## Project Overview

This is a production-ready Django 5.2 LTS boilerplate configured for
**QueryMaster**. The Python package is `querymaster/`.

Before changing the RAG data model, ingestion, chunking, embeddings, retrieval,
reranking, citations, or AI APIs, read `docs/specs.md`. Follow `docs/plan.md` for
implementation order and phase completion criteria.

## Development Commands

Run all application operations inside Docker containers through Makefile
targets. Do not assume a local virtual-environment workflow.

```bash
# Start the development environment
make dev.build
make dev.up.d

# Shell access
make dev.dcshell    # Bash in the Django container
make dev.dshell     # Django shell with secrets sourced
make dev.ipshell    # IPython shell

# Database
make dev.makemigrations
make dev.migrate
make dev.psql

# Run the full test suite (test containers plus coverage)
make test

# Recompile dependencies after editing config/requirements/*.in
make cr

# Lint and format through pre-commit or Ruff
pre-commit run --all-files
ruff check .
ruff format .
```

`DJANGO_SETTINGS_MODULE` is set by the Docker entrypoint for each environment:
`config.settings.dev`, `config.settings.test`, `config.settings.stage`, or
`config.settings.prod`.

## Architecture

### Settings

Settings are split by environment and concern and imported additively:

- `config/settings/base.py`: shared database, Celery, DRF, JWT, allauth,
  Constance, and logging configuration
- `config/settings/dev.py`: development settings, including `DEBUG=True` and
  the console email backend
- `config/settings/prod.py`: imports base, Brevo, S3, and Sentry settings and
  sets `DEBUG=False`
- `config/settings/brevo.py`: Anymail/Brevo email backend
- `config/settings/s3.py`: AWS S3 static and media storage
- `config/settings/sentry.py`: Sentry configuration
- `config/settings/constance.py`: runtime configuration

### Secrets

Application secrets come from Infisical through the `infisical-agent` sidecar.
It writes secrets to `/secrets/app.env`, which is sourced before Django commands
run. The root `.env` contains only Docker Compose bootstrap values and Infisical
credentials; do not put application secrets there.

### Repository Layout

```text
querymaster/
  core/          # Base models, pagination, logging, and health check
  users/         # Custom email-based User model without a username field
config/
  settings/      # Settings split by environment and concern
  requirements/  # Per-environment input and pinned dependency files
  nginx/         # Stage and production Nginx configuration
  env/           # Environment examples and test environment values
```

### API

Keep APIs versioned under `api/v1/` within each Django app:

- `querymaster/core/api/v1/`: health check endpoint
- `querymaster/users/api/v1/`: registration, login, logout, password, Google
  OAuth, and account-deletion endpoints

Current URL prefixes are `/api/v1/core/` and `/api/v1/users/`. Swagger UI is
available at `/swagger/` and requires HTTP Basic authentication.

### Authentication

Authentication uses JWT through `djangorestframework-simplejwt`, managed by
`dj-rest-auth` and `django-allauth`. Authentication is email-only; the custom
`User` model has no `username` field. Email verification is mandatory. The OTP
flow is controlled by the `ENABLE_OTP` environment variable.

### Background Work, Caching, and Runtime Configuration

- Celery uses Redis as its broker and `django-db` as its result backend.
- Celery Beat uses the database-backed `django_celery_beat` scheduler.
- Flower is exposed on port 5555.
- Django's Redis cache uses database index 1.
- `django-constance` uses Redis database index 0 for runtime configuration,
  including `MAX_LOG_BODY_CHARS_LIMIT`.

### Logging

`LoggingMiddleware` logs each request and response with a UUID correlation ID,
IP address, method, path, status code, and truncated response body. Supporting
code lives in `querymaster/core/logging/`.

## Coding Conventions

- Use class-based views.
- Keep views thin and put business logic in service modules.
- Use the Django ORM. Only use raw SQL when demonstrably required for
  performance.
- Use `select_related` and `prefetch_related` to avoid unnecessary related
  object queries.
- Do not use Django signals.
- Do not introduce custom exception classes; use Django's built-in error
  handling.
- Handle expected exceptions with `try`/`except` in business logic or views.

## Adding a Django App

1. Create the app under `querymaster/`.
2. Add it to `CUSTOM_APPS` in `config/settings/base.py`.
3. Add `api/v1/urls.py` and `api/v1/views.py` within the app.
4. Register its URL prefix in `config/urls.py`.
