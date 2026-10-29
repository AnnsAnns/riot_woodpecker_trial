---
title: Worker fleet and web UI
description: The legacy murdock-worker stack, RIOT build images, and the murfrog UI.
---

This page covers the pieces around the modern API that are still used in RIOT
deployments or by maintainers.

## Legacy worker fleet

The `murdock-worker/` repository is a Docker Compose stack for the old
`dwq`/`disque` architecture:

| Service | Role |
| --- | --- |
| `worker` | `riot/murdock-worker` running `dwqw`, listening on board/queue names |
| `redis-ccache` | Redis with a Unix socket used as the ccache backend |
| `ssh_bridge` | autossh tunnel to the control node's disque, redis, and vector |
| `watchtower` | Keeps worker images up to date |
| `vector` | Collects host, Redis, and Vector metrics and forwards them upstream |
| `redis_exporter` | Prometheus metrics for the ccache Redis |

It is configured with `MURDOCK_HOSTNAME`, `MURDOCK_SSH_HOST`,
`MURDOCK_QUEUES`, `MURDOCK_JOBS`, `MURDOCK_BUILD_TMPFS_GIGS`, and
`MURDOCK_CCACHE_MAXSIZE_GIGS`. A worker is typically given one job per physical
core and at least 2 GB of RAM, plus 8 GB for ccache.

The modern server does not require this stack. It is documented because RIOT's
CI history and the `murdock-scripts` result format are tied to it.

## RIOT build images

`riotdocker/` builds the `riot/riotbuild` images. They contain the cross
toolchains, `make`, Python, and the RIOT build dependencies. A Murdock job in
Docker mode usually runs with:

```yaml
tasks:
  - image: riot/riotbuild:latest
    command: ./build.sh
```

## `murfrog` web UI

`murfrog` is the React/Vite UI for Murdock. It talks to the REST API and the
status WebSocket and provides:

- a job list with filters for all/PR/branch/merge-queue/nightly/tag jobs,
- state filters, PR number and label filters, and search,
- a job detail view with output, build/test results, and artifacts,
- maintainer actions (cancel, abort, restart) after GitHub login,
- live updates over `/ws/status`.

### Configuration

```dotenv
VITE_MURDOCK_HTTP_BASE_URL=https://ci.riot-os.org
VITE_MURDOCK_WS_URL=wss://ci.riot-os.org/ws/status
VITE_GITHUB_REPO=RIOT-OS/RIOT
VITE_GITHUB_CLIENT_ID=...
VITE_GITHUB_GATEKEEPER_URL=https://ci.riot-os.org/github
VITE_GITHUB_REDIRECT_URI=https://ci.riot-os.org/
VITE_GITHUB_SCOPE=read:user
VITE_ITEMS_DISPLAYED_STEP=50
```

The UI uses these API paths:

```text
GET    /jobs?<query>
GET    /job/<uid or branch/...|tag/...|commit/...|pr/...>
DELETE /job/<uid>
POST   /job/<uid>
GET    /results/<uid>/...
GET    /github/authenticate/<code>   (OAuth gatekeeper)
```

### GitHub login

The browser cannot exchange a GitHub OAuth code directly because GitHub's token
endpoint has no CORS headers. `murfrog` uses a small gatekeeper:

```text
GET {VITE_GITHUB_GATEKEEPER_URL}/authenticate/{code} -> {"token": "..."}
```

Murdock itself implements this exchange at `/github/authenticate/{code}`. A
Cloudflare Worker implementation is also included in the `murfrog` repository.

The `read:user` scope is enough for the profile request and the repo
`permissions.push` check used to show maintainer controls. Browsing the
dashboard requires no login.

## `murdock/frontend`

The upstream `murdock` repository also contains a tiny Starlette app that serves
a built `frontend/build` directory. The main React UI in active use is
`murfrog`. The bundled frontend is a minimal static host.
