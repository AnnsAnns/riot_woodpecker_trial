---
title: Running locally
description: Start a Murdock API and MongoDB with Docker Compose, and understand the limits.
---

This repository includes a minimal local stack in `murdock-backend/`. It runs
the real API server from the `murdock/` submodule, using the published
`murdockng/murdock:latest` image for its Python dependencies.

## Start the stack

```sh
cd murdock-backend
mkdir -p data
docker compose up -d
```

The first start pulls MongoDB 7 and the Murdock image. Once it is up:

```sh
curl http://localhost:8000/jobs
# []

curl http://localhost:8000/openapi.json | head
open http://localhost:8000/api
```

The Swagger UI is served at `/api`, the raw schema at `/openapi.json`, and the
job API at `/jobs`.

Stop it with:

```sh
docker compose down
# add -v to delete the MongoDB volume and all job history
```

## What the stack contains

| Service | Purpose |
| --- | --- |
| `mongo` | MongoDB 7, persisted in the `mongo-data` volume |
| `murdock` | The API server, with `../murdock/murdock` and `../murdock/murdock.py` bind-mounted read-only |

The image from 2023 ships Python 3.10, `fastapi 0.92.0`, `pydantic 1.10.5`, and
`motor 3.1.1`, which match the checked-out Murdock `main` branch. The server
code is not baked into the image. It comes from the bind mount, so pulling the
submodule is enough to update it after a restart.

The image runs as UID 1000. If your user ID is different, change the owner of
`data/` or add a `user:` override to the `murdock` service.

## Checks performed

These checks passed on the local stack:

- `GET /jobs` returned `200` with a JSON list.
- `GET /openapi.json`, `GET /api`, and `GET /metrics` returned `200`.
- `GET /job/branch/master` and the branch badge returned `404` when no job existed.
- `GET /health` returned `404`, so the guide does not claim a health endpoint.
- The WebSocket at `/ws/status` accepted a connection.
- `POST /job/branch`, `POST /job/{uid}`, `DELETE /job/{uid}`, and `DELETE /jobs`
  returned `401` without a GitHub OAuth token.
- `PUT /job/{uid}/status` returned `400` for an unknown job.
- A real script-mode job ran `scripts/run.sh` and returned `passed`. The job
  wrote `output.txt`, appeared in `/jobs`, and `/results/<uid>/output.txt`
  returned the file.

## Legacy backend file

For a full RIOT job with the `murfrog` UI, see
[Full RIOT demo stack](/getting-started/riot-demo/).

The original `murdock-backend/docker-compose` file was the legacy
disque/redis/ssh/vector backend. It was not a complete Murdock stack. It is
preserved as `murdock-backend/docker-compose.legacy.yml`.

That file defined only:

- `disque`: the old queue,
- `disque_exporter`: metrics for the queue,
- `redis`: the old ccache and test cache,
- `ssh`: the worker SSH bridge,
- `vector`: metrics forwarding.

It did not contain the API server, MongoDB, or a UI. It did not start as-is:

- `disque_exporter` built from the missing `./disque-exporter` directory.
- `ssh` mounted missing `./ssh-host-keys` and `./ssh-slave-keys`.
- `vector` mounted a missing `./vector.toml`.
- The published ports used placeholder IPv6 addresses
  (`[2a01:4f9:...::1]` and `[IPIPIPIP::1]`). Docker rejected the second address
  with `invalid IP address: IPIPIPIP::1`.

The active `docker-compose.yml` file replaces that stack for local use. The legacy
file is still useful as a reference for the old dwq/disque worker design.

## Limitations of the local stack

- No GitHub integration. The GitHub configuration uses dummy values, so manual jobs and
  webhooks cannot fetch commits. Replace `GITHUB_REPO`, the GitHub App/OAuth
  credentials, the webhook secret, and `GITHUB_API_TOKEN` to use them.
- No frontend. The API's Swagger UI is available at `/api`. To use the
  `murfrog` UI:

  ```sh
  cd ../murfrog
  VITE_MURDOCK_HTTP_BASE_URL=http://localhost:8000 \
  VITE_MURDOCK_WS_URL=ws://localhost:8000/ws/status \
  npm install && npm run dev
  ```

- In-process jobs. `MURDOCK_RUN_IN_DOCKER=0` runs the demo `run.sh` inside
  the API container. Enable Docker mode and mount the Docker socket if you want
  per-job containers.
- No authentication setup. API write endpoints require a GitHub OAuth token
  with push/admin permission on `GITHUB_REPO`. With dummy configuration those calls
  will fail at the GitHub permission check.

## Direct execution (advanced)

You can run the server directly with `uvicorn` if you provide compatible Python
dependencies. The checked-out `main` branch uses Pydantic v1 APIs
(`BaseSettings`, `.dict()`), so a modern environment with Pydantic v2 will fail
at import. The upstream `pydantic_2_fixes` branch contains the port if you want
to run it on current FastAPI/Pydantic.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install 'pydantic<2' 'fastapi<0.100' uvicorn motor httpx PyYAML \
  aiosmtplib prometheus-fastapi-instrumentator structlog asyncpg orjson
ENV_FILE=../.env uvicorn murdock.main:app --reload --reload-dir murdock
```

## Tests

The upstream test suite uses `pytest` and `tox`:

```sh
cd murdock
python3 -m pip install -r requirements.txt
tox
```

Tests cover the API, job scheduler, database backends, GitHub helpers,
notifications, templates, and models.
