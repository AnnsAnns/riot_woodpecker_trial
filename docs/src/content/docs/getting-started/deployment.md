---
title: Deployment
description: Deploy Murdock with Docker Compose, GitHub, a database, and job images.
---

Murdock is usually deployed as a Docker Compose stack:

- `murdock`: the FastAPI API server,
- `mongo` (or PostgreSQL): job history,
- optionally `frontend`: the React web UI,
- optionally `proxy`: Traefik in the upstream compose file.

The upstream `murdock/docker-compose.yml` is a good starting point, but it
expects a built frontend and a filled `.env`. The minimal local alternative in
this repository is described in [Running locally](/getting-started/local-development/).

## Requirements

- Docker and Docker Compose.
- A GitHub repository and an account/token that can read the repository, write
  commit statuses, and post issue comments.
- A GitHub OAuth application for browser login, if you use the web UI.
- A GitHub webhook pointing at `https://<your-host>/github/webhook`.
- A writable work directory and a directory containing the job script.
- MongoDB or PostgreSQL. MongoDB is the default.

## Environment

Copy `.env.example` to `.env` and fill in at least:

```dotenv
MURDOCK_BASE_URL=https://ci.example.org
MURDOCK_WORK_DIR=/var/lib/murdock-data
MURDOCK_SCRIPTS_DIR=/var/lib/murdock-scripts
MURDOCK_SCRIPT_NAME=run.sh

MURDOCK_DB_TYPE=mongodb
MURDOCK_DB_HOST=mongo
MURDOCK_DB_PORT=27017
MURDOCK_DB_NAME=murdock

MURDOCK_GITHUB_APP_CLIENT_ID=...
MURDOCK_GITHUB_APP_CLIENT_SECRET=...
GITHUB_REPO=org/repo
GITHUB_WEBHOOK_SECRET=...
GITHUB_API_TOKEN=...
```

See [Environment variables](/reference/environment-variables/) for the full
list and defaults.

:::caution
`MURDOCK_WORK_DIR` and `MURDOCK_SCRIPTS_DIR` must exist before the server starts.
Murdock checks both paths at import time and refuses to start otherwise.
:::

## GitHub setup

1. OAuth application: create one with the callback
   `https://<your-host>/authorize` (the browser login flow uses the same OAuth
   code exchange through `/github/authenticate/{code}`). Put the
   client ID and secret in `MURDOCK_GITHUB_APP_CLIENT_ID` and
   `MURDOCK_GITHUB_APP_CLIENT_SECRET`.
2. API token: a token that can read the repo, set statuses, and comment.
   Put it in `GITHUB_API_TOKEN`.
3. Webhook: point it at `https://<your-host>/github/webhook`, set the
   secret to `GITHUB_WEBHOOK_SECRET`, and select the `push` and `pull_request`
   events. Murdock checks the `X-Hub-Signature-256` header.
4. Repository: `GITHUB_REPO` must match the webhook repository's
   `full_name`, otherwise events are rejected as `Invalid repo`.

## Job execution modes

Murdock supports two execution modes:

- Script mode (`MURDOCK_RUN_IN_DOCKER=0`): runs
  `$MURDOCK_SCRIPTS_DIR/$MURDOCK_SCRIPT_NAME` directly in the API container.
  The build tools must be installed there.
- Docker mode (`MURDOCK_RUN_IN_DOCKER=1`): runs a `docker run` container
  per task. This requires the Docker socket, a host work directory, and the
  Docker group ID. It is how the upstream compose runs RIOT jobs with
  `riot/riotbuild`.

See [Tasks and execution](/features/tasks-and-execution/) for details.

## Reverse proxy and UI

The upstream compose uses Traefik. The important routes are:

- `/` and the SPA fallback → the frontend container,
- `/api`, `/jobs`, `/job`, `/ws`, `/results`, `/metrics`, `/github` → the API.

If you use the separate `murfrog` UI, point it at the API with:

```sh
VITE_MURDOCK_HTTP_BASE_URL=https://ci.example.org
VITE_MURDOCK_WS_URL=wss://ci.example.org/ws/status
VITE_GITHUB_REPO=org/repo
```

The UI is a static single-page app (SPA) and needs a server-side fallback to `index.html` for client-side routes.

## Database choice

Murdock supports MongoDB (`motor`) and PostgreSQL (`asyncpg`). The database only
stores finished jobs. Queued and running jobs live in memory. Restarting the
server loses in-flight work but keeps history.

```dotenv
MURDOCK_DB_TYPE=postgresql
MURDOCK_DB_HOST=postgres
MURDOCK_DB_PORT=5432
MURDOCK_DB_NAME=murdock
MURDOCK_DB_AUTH_USER=murdock
MURDOCK_DB_AUTH_PASSWORD=secret
```

PostgreSQL is a later addition in the codebase. MongoDB remains the default.

## Operational notes

- `MURDOCK_NUM_WORKERS` controls in-process concurrency, not container scaling.
- `MURDOCK_CANCEL_ON_UPDATE=1` stops older jobs for the same PR/ref when a new
  event arrives.
- `MURDOCK_STORE_STOPPED_JOBS` keeps stopped jobs in history.
- `MURDOCK_ENABLE_COMMIT_STATUS` and `MURDOCK_ENABLE_PR_COMMENT` can disable
  GitHub writes during testing.
- `MURDOCK_ENABLE_NOTIFICATIONS` is off by default.
