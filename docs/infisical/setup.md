# Infisical Setup Guide

This guide walks through setting up Infisical as the secret manager for this boilerplate. Once set up, all app secrets are stored in Infisical cloud and injected into containers at runtime via the Infisical agent sidecar.

For the agent architecture and how secrets flow into containers, see [Infisical_agent.md](./Infisical_agent.md).

---

## Prerequisites

- Access to an Infisical instance (cloud at [infisical.com](https://infisical.com) or self-hosted)
- Docker and Docker Compose installed locally

---

## Step 1 — Create a Project

1. Log in to your Infisical instance
2. Click **New Project** and give it the same name as your Django project
3. Note down the **Project ID** and **Project Slug** — you will need these in `.env`

---

## Step 2 — Create Environments

Infisical projects come with `development`, `staging`, and `production` environments by default.

Rename or confirm the slugs match what this boilerplate expects:

| Dashboard name | Slug used in `.env` |
| -------------- | ------------------- |
| Development | `dev` |
| Staging | `staging` |
| Production | `prod` |

To check or change a slug: **Project Settings → Environments**

---

## Step 3 — Create the `ENV` Folder

Inside **each environment** (`dev`, `staging`, `prod`), create a folder named `ENV` to hold all secrets:

1. Open the environment (e.g. `dev`)
2. Click **Add Folder** → name it `ENV`
3. Open the `ENV` folder — all secrets for that environment go here

Keeping secrets inside a named folder rather than at the root has two benefits:
- Secrets are visually organised in the dashboard
- `INFISICAL_SECRET_PATH=/ENV` in `.env` makes it immediately clear where secrets live

---

## Step 4 — Add Secrets

Inside the `ENV` folder for **each environment**, add all the key-value pairs listed in `config/env/infisical.example`.

Variables marked `# * per env` in that file are the ones that differ between environments. Everything else can be copied as-is and updated with real values.

**Common per-environment differences:**

| Variable | dev | staging | prod |
| -------- | --- | ------- | ---- |
| `ENV` | `dev` | `staging` | `prod` |
| `DJANGO_SETTINGS_MODULE` | `config.settings.dev` | `config.settings.stage` | `config.settings.prod` |
| `BASE_URL` | `http://localhost:8000` | `https://staging.example.com` | `https://example.com` |
| `DJANGO_ALLOWED_HOSTS` | `*` | `staging.example.com` | `example.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `http://localhost:8000` | `https://staging.example.com` | `https://example.com` |
| `SERVER_NAME` | `localhost` | `staging.example.com` | `example.com` |

> **Note on JSON values:** If any secret value is a JSON string (e.g. `VAPID_CLAIMS`), use double quotes inside the value — not single quotes. Infisical stores raw strings; single-quoted JSON is invalid.

> **Note on AWS S3 variables:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_CUSTOM_DOMAIN`, `AWS_STATIC_LOCATION`, and `AWS_MEDIA_LOCATION` are only read by `config/settings/s3.py` (imported into `config.settings.prod` for S3-backed static/media storage). They're not needed in the `dev` or `staging` environments.
>
> **Bucket prerequisite:** `config/settings/s3.py` sets `AWS_DEFAULT_ACL = None`, which assumes the bucket has Object Ownership set to "ACLs disabled" (AWS's own recommended default for new buckets) and relies on a bucket policy (not per-object ACLs) to grant public read access to static/media files. When provisioning the real prod bucket, disable ACLs and attach a bucket policy allowing `s3:GetObject` on `arn:aws:s3:::<bucket-name>/*` — without it, uploaded files will 403 even though the app itself works correctly.

---

## Step 5 — Create a Machine Identity

The Infisical agent authenticates using a Machine Identity with Universal Auth.

1. Go to **Project → Access Control → Machine Identities**
2. Click **Create Identity** → give it a name (e.g. `docker-agent`)
3. Select **Universal Auth** as the auth method
4. Under the identity, click **Add Client Secret** and copy both:
   - `Client ID`
   - `Client Secret`
5. Assign the identity **read-only** access to the project:
   **Project → Access Control → Machine Identities → [identity] → Project Role → Viewer**

---

## Step 6 — Configure `.env`

Copy the example and fill in your values:

```bash
cp config/env/.env.example .env
```

Your `.env` should look like this:

```
# Docker Compose bootstrap
PROJECT=your-project-name
REQUIREMENT_FILE=config/requirements/dev.txt

# Infisical credentials
INFISICAL_HOST=https://app.infisical.com          # or your self-hosted URL
INFISICAL_PROJECT_ID=<from Step 1>
INFISICAL_PROJECT_SLUG=<from Step 1>
INFISICAL_ENVIRONMENT_SLUG=dev                    # dev / staging / prod
INFISICAL_SECRET_PATH=/ENV
INFISICAL_CLIENT_ID=<from Step 5>
INFISICAL_CLIENT_SECRET=<from Step 5>
```

Set `INFISICAL_ENVIRONMENT_SLUG` to match the server:
- Local dev machine → `dev`
- Staging server → `staging`
- Production server → `prod`

For variables consumed by compose `command:` (for example gunicorn workers/threads),
see the escape pattern note in `Infisical_agent.md`.

---

## Step 7 — Start the Stack

```bash
make dev.up          # foreground
make dev.up.d        # detached (background)
```

The Infisical agent starts first, fetches all secrets for the configured environment, and writes them to a shared volume. All other containers wait for the secrets file before starting.

> TODO (during setup): Validate the `make *.secret.reload` behavior against your selected compose file. It restarts only services that exist in that environment (some environments may omit `celery`, `celery_beat`, or `flower`).

---

## Verifying It Works

**Check what the agent wrote:**
```bash
docker exec -it $(docker ps -qf name=infisical-agent) cat /secrets/app.env
```

**Check agent logs:**
```bash
docker compose -f docker-compose.dev.yml logs infisical-agent
```

**Check a container received the secrets:**
```bash
docker exec -it $(docker ps -qf name=django) printenv | grep DJANGO_SECRET_KEY
```

---

## Updating a Secret

1. Update the value in the Infisical dashboard
2. The agent picks it up within 60 seconds and rewrites `/secrets/app.env`
3. Restart all app containers to apply:
   ```bash
   make dev.secret.reload     # development
   make stage.secret.reload   # staging
   make prod.secret.reload    # production
   ```

---

## Troubleshooting

**Containers stuck on `Waiting for Infisical agent to write secrets...`**
- Check agent logs: `docker compose -f docker-compose.dev.yml logs infisical-agent`
- Verify `INFISICAL_CLIENT_ID` and `INFISICAL_CLIENT_SECRET` in `.env` are correct
- Verify `INFISICAL_HOST` is reachable from the Docker network
- After 120 seconds with no secrets file, containers will exit with an error — check the exit message for details

**`PROJECT` or `REQUIREMENT_FILE` warnings on `docker compose up`**
These variables are read by Docker Compose before any container starts. They must be in `.env` — they cannot come from Infisical. Ensure `.env` exists and has both variables set.
