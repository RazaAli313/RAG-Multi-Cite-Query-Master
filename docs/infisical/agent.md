# Infisical Agent — How It Works

## What Is the Infisical Agent?

The Infisical Agent is a sidecar process that runs alongside your application. It authenticates with Infisical, fetches all secrets, and writes them to a shared file. The application reads that file on startup — no SDK, no API calls inside Django.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Docker Compose                                         │
│                                                         │
│  ┌──────────────────┐     shared volume (named)         │
│  │  infisical-agent │ ──► /secrets/app.env ──────────┐  │
│  │                  │                                 │  │
│  │  Polls Infisical │                                 ▼  │
│  │  every 60s       │              ┌─────────────────────┐
│  └──────────────────┘              │  django / web_worker │
│                                    │                      │
│                                    │  Entrypoint waits    │
│                                    │  for app.env, then   │
│                                    │  sources it and      │
│                                    │  starts the app      │
│                                    └─────────────────────┘
└─────────────────────────────────────────────────────────┘
```

Only the Infisical credentials (`CLIENT_ID`, `CLIENT_SECRET`) live in `.env`. Every other secret (database URL, Django secret key, AWS keys, etc.) lives in Infisical.

---

## Files Involved

| File                                    | Purpose                              |
| --------------------------------------- | ------------------------------------ |
| `scripts/infisical-agent-entrypoint.sh` | Starts the agent container           |
| `scripts/docker-entrypoint.sh`          | Starts the Django/worker containers  |
| `docker-compose.dev.yml`                | Wires everything together            |
| `.env`                                  | Holds only the Infisical credentials |

---

## Step-by-Step: First Time Setup

### 1. Add credentials to `.env`

Only these five variables are needed. Nothing else.

```bash
INFISICAL_HOST=https://secrets.cogentlabs.co
INFISICAL_PROJECT_ID=<your-project-id>
INFISICAL_PROJECT_SLUG=<your-project-slug>
INFISICAL_ENVIRONMENT_SLUG=dev
INFISICAL_SECRET_PATH=/
INFISICAL_CLIENT_ID=<your-machine-identity-client-id>
INFISICAL_CLIENT_SECRET=<your-machine-identity-client-secret>
```

Get `CLIENT_ID` and `CLIENT_SECRET` from Infisical:
`Project → Access Control → Machine Identities → Universal Auth`

### 2. Add your secrets to Infisical

In the Infisical dashboard, go to your project → `dev` environment and add all secrets your app needs (e.g. `DJANGO_SECRET_KEY`, `DATABASE_URL`, `AWS_ACCESS_KEY_ID`, etc.).

**JSON values** must use double quotes (valid JSON), not single quotes:

```
VAPID_CLAIMS  →  {"sub": "mailto:you@example.com"}   ✅
VAPID_CLAIMS  →  {'sub': 'mailto:you@example.com'}   ❌
```

### 3. Start the stack

```bash
make dev.dc
# or
docker compose -f docker-compose.dev.yml up
```

---

## What Happens on First Start

```
1. infisical-agent starts
   │
   ├─ Reads INFISICAL_CLIENT_ID and INFISICAL_CLIENT_SECRET from .env
   ├─ Writes them to /tmp/credentials/ inside the container
   ├─ Authenticates with Infisical (Universal Auth)
   ├─ Fetches all secrets for the configured project + environment
   └─ Writes /secrets/app.env (shared volume) in this format:
         export DJANGO_SECRET_KEY='abc123...'
         export DATABASE_URL='postgresql://user:pass@db:5432/dbname'
         export AWS_ACCESS_KEY_ID='AKIA...'
         ...

2. django / web_worker start (depends_on: infisical-agent)
   │
   ├─ docker-entrypoint.sh runs
   ├─ Polls every 2 seconds: does /secrets/app.env exist yet?
   ├─ Once found: sources the file → all secrets enter os.environ
   └─ Hands off to uvicorn / manage.py run_huey
```

Total wait time is usually under 5 seconds on a good connection.

---

## What Happens on Subsequent Deploys / Restarts

The agent keeps running and **re-fetches secrets every 60 seconds**. It updates `/secrets/app.env` automatically whenever secrets change in Infisical.

When you restart the stack:

```
1. Docker destroys and recreates containers
   - The named volume `infisical-secrets` persists between restarts
     (unless you run `docker compose down -v`)

2. infisical-agent starts again
   - Re-authenticates and writes fresh secrets immediately

3. django starts again
   - Entrypoint finds /secrets/app.env (may already exist from the volume)
   - Sources it and starts in < 2 seconds
```

**If you update a secret in Infisical** while the stack is running:

- The agent picks it up within 60 seconds and rewrites `/secrets/app.env`
- Django does **not** hot-reload secrets — you need to restart the django container:
  ```bash
  docker compose -f docker-compose.dev.yml restart django
  ```

---

## What Happens If Infisical Is Unreachable

- The agent keeps retrying (3 retries with exponential backoff by default)
- Django's entrypoint keeps polling every 2 seconds waiting for `/secrets/app.env`
- If there is no previous file and Infisical is down, Django will wait indefinitely

---

## Adding a New Secret

1. Add the secret in the Infisical dashboard
2. Within 60 seconds the agent rewrites `/secrets/app.env`
3. Restart the django container to pick it up:
   ```bash
   docker compose -f docker-compose.dev.yml restart django
   ```
4. If it is a new Django settings variable, add it to `base.py` as well:
   ```python
   MY_NEW_SETTING = env("MY_NEW_SECRET_KEY")
   ```

---

## Different Environments (dev / staging / production)

The same scripts work for all environments. The environment is controlled by `INFISICAL_ENVIRONMENT_SLUG` in `.env` on each server:

| Server     | `.env` value                         |
| ---------- | ------------------------------------ |
| Local dev  | `INFISICAL_ENVIRONMENT_SLUG=dev`     |
| Staging    | `INFISICAL_ENVIRONMENT_SLUG=staging` |
| Production | `INFISICAL_ENVIRONMENT_SLUG=prod`    |

The agent reads this variable at startup and fetches secrets for the correct environment automatically.

---

## Variables Consumed by Compose `command:`

If a variable is used inside a compose `command:` string, escape it as `$$VAR` so Docker
Compose passes it through and expansion happens inside the container at runtime.

For gunicorn, use:

```bash
--workers $$GUNICORN_WORKERS --threads $$GUNICORN_THREADS
```

This ensures values sourced from `/secrets/app.env` are used when the process starts.

Do not apply this to bootstrap variables that Compose must read before containers start
(for example `PROJECT`, `REQUIREMENT_FILE`, and `INFISICAL_*` in `.env`).

---

## Debugging

**Check what the agent wrote:**

```bash
docker exec -it $(docker ps -qf name=infisical-agent) cat /secrets/app.env
```

**Check agent logs:**

```bash
docker compose -f docker-compose.dev.yml logs infisical-agent
```

**Check django received the secrets:**

```bash
docker exec -it $(docker ps -qf name=django) printenv | grep DJANGO_SECRET_KEY
```

**Force a fresh start (wipes the secrets volume):**

```bash
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up
```