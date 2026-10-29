---
title: Architecture
description: Components, job flow, and the two Murdock architectures.
---

Murdock is deliberately small: a FastAPI application owns all state, and work is
performed by asynchronous worker tasks inside the same process. External systems
provide the forge integration, persistence, and the actual build environment.

## Components

```text
                       ┌──────────────────────────────┐
  GitHub webhook ─────▶│        FastAPI server        │
  REST clients   ─────▶│  /jobs  /job/...  /ws/status │
                       └──────────────┬───────────────┘
                                      │
                 ┌────────────────────┼────────────────────┐
                 │                    │                    │
          ┌──────▼──────┐      ┌──────▼──────┐      ┌──────▼──────┐
          │   MongoDB   │      │  job queue  │      │   GitHub    │
          │ PostgreSQL  │      │  + workers  │      │  REST API   │
          └─────────────┘      └──────┬──────┘      └─────────────┘
                                      │
                         ┌────────────┴────────────┐
                         │                         │
                  ┌──────▼──────┐           ┌──────▼──────┐
                  │  run.sh /   │           │ docker run  │
                  │ task script │           │ job image   │
                  └─────────────┘           └─────────────┘
```

| Component | Role |
| --- | --- |
| FastAPI app (`murdock/main.py`) | HTTP API, WebSocket, static results, OpenAPI |
| `Murdock` (`murdock/murdock.py`) | Queues, workers, event handling, job lifecycle |
| `MurdockJob` (`murdock/job.py`) | Per-job state, environment, output, artifacts |
| `Task` (`murdock/task.py`) | Runs a script or Docker container and captures output |
| Database (`murdock/database/`) | Finished-job history and queries |
| GitHub client (`murdock/github.py`) | Commit/PR/branch lookups, statuses, comments, `.murdock.yml` |
| Notifier (`murdock/notify.py`) | Mail and Matrix notifications |
| Web UI (`murfrog`, `murdock/frontend`) | Browser UI over the REST API and WebSocket |

## Job flow

1. Event arrives. `POST /github/webhook` checks the HMAC signature and
   dispatches `push` or `pull_request` events. Manual jobs arrive through
   `POST /job/branch`, `/job/tag`, or `/job/commit`.
2. Configuration is loaded. Murdock fetches `.murdock.yml` from the exact
   commit through the GitHub contents API. Missing or invalid files fall back to
   `MurdockSettings()` defaults.
3. Policy is applied. The PR ready label, commit skip keywords, and push
   branch/tag allowlists determine whether a job is created. Closing a PR or
   deleting a ref cancels matching work.
4. Job is queued. If `cancel_on_update` is enabled, older queued or running
   jobs for the same PR/ref are canceled or stopped first.
5. Worker picks it up. `MURDOCK_NUM_WORKERS` async tasks consume the normal
   queue. Fasttracked jobs use a second queue when all workers are busy.
6. Tasks run. Each task is executed in the job work directory. Output lines
   are appended to `output.txt` and streamed to WebSocket clients.
7. Result is recorded. The job state becomes `passed`, `errored`, or
   `stopped`. GitHub statuses and PR comments are updated, notifications are
   sent, and the job is inserted into the database.

## Storage

Each job gets a directory under `MURDOCK_WORK_DIR` named after its UID. It
contains `output.txt`, any declared artifacts, and any files produced by the
task. The `/results` route serves this directory over HTTP. Finished-job
metadata lives in MongoDB or PostgreSQL. See
[Results and artifacts](/features/results-and-artifacts/).

## The legacy architecture

The older Murdock control node used:

- a `dwq` client to push jobs onto queues,
- `disque` as the queue backend,
- Docker worker containers running `dwqw`,
- an SSH bridge for workers to reach the control node's disque/redis,
- `murdock-scripts/build.sh` to discover jobs and fan them out.

`murdock-ng` removes the external queue and worker fleet: jobs are queued and
executed by asyncio tasks in the API process. The old stack is still relevant
for understanding RIOT's historical CI behavior and the `murdock-worker`
repository, but it is not needed to run the modern server.

:::note
The original `murdock-backend/docker-compose` file was the legacy
disque/redis/ssh/vector backend, not a complete Murdock API stack. It is
preserved as `docker-compose.legacy.yml`. See
[Running locally](/getting-started/local-development/) for the working stack.
:::
