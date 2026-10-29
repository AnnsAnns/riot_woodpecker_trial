---
title: Environment variables
description: Complete reference for Murdock server, database, GitHub, CI, notifier, and Docker configuration.
---

Murdock reads configuration from environment variables and an optional `.env` file.
The file is selected by `ENV_FILE` (default: `murdock/../.env`).

Configuration values without a default are required. The server does not start if they are missing.

## Global

| Variable | Default | Description |
| --- | --- | --- |
| `MURDOCK_PROJECT` | `default` | Project name. Murdock uses it in Docker container/network names |
| `MURDOCK_BASE_URL` | `http://localhost:8000` | Public base URL used in links and statuses |
| `MURDOCK_WORK_DIR` | `/var/lib/murdock-data` | Job work directories and `/results` root |
| `MURDOCK_HOST_WORK_DIR` | `<tmp>/murdock-data` | Host path corresponding to `MURDOCK_WORK_DIR` for Docker jobs |
| `MURDOCK_SCRIPTS_DIR` | `/var/lib/murdock-scripts` | Directory containing the job script |
| `MURDOCK_SCRIPT_NAME` | `run.sh` | Script executed in script mode |
| `MURDOCK_RUN_IN_DOCKER` | `false` | Run tasks with `docker run` instead of directly |
| `MURDOCK_USER_UID` | `1000` | UID for Docker task containers |
| `MURDOCK_USER_GID` | `1000` | GID for Docker task containers |
| `MURDOCK_DOCKER_DEFAULT_TASK_IMAGE` | `ubuntu:latest` | Image used when a task has no `image` |
| `MURDOCK_DOCKER_VOLUMES` | `{}` | Extra Docker volumes (host→container map) |
| `MURDOCK_DOCKER_CPU_LIMIT` | `1.0` | `--cpus` for Docker tasks |
| `MURDOCK_DOCKER_MEM_LIMIT` | `1g` | `--memory` for Docker tasks |
| `MURDOCK_ACCEPTED_EVENTS` | `["push","pull_request"]` | Webhook event types |
| `MURDOCK_NUM_WORKERS` | `1` | In-process worker tasks |
| `MURDOCK_CUSTOM_ENV` | `{}` | Extra environment variables for every job |
| `MURDOCK_LOG_LEVEL` | `DEBUG` | Murdock log level |
| `UVICORN_LOG_LEVEl` | `INFO` | Uvicorn access log level (note the lowercase `l` in `LEVEl`) |
| `MURDOCK_LOG_OUTPUT` | `console` | Log output mode |
| `MURDOCK_MAX_FINISHED_LENGTH_DEFAULT` | `25` | Default `limit` for `GET /jobs` |
| `MURDOCK_CANCEL_ON_UPDATE` | `true` | Cancel/stop matching jobs on new events |
| `MURDOCK_ENABLE_COMMIT_STATUS` | `true` | Write GitHub commit statuses |
| `MURDOCK_COMMIT_STATUS_CONTEXT` | `Murdock` | GitHub status context |
| `MURDOCK_ENABLE_PR_COMMENT` | `true` | Allow PR comments |
| `MURDOCK_STORE_STOPPED_JOBS` | `true` | Keep stopped jobs and work dirs |
| `MURDOCK_NOTIFIER_ENABLE` | `false` | Enable mail/Matrix notifications |

:::caution
`MURDOCK_WORK_DIR` and `MURDOCK_SCRIPTS_DIR` must exist at startup. A missing
directory raises a validation error.
:::

## Database

| Variable | Default | Description |
| --- | --- | --- |
| `MURDOCK_DB_TYPE` | `mongodb` | `mongodb` or `postgresql` |
| `MURDOCK_DB_HOST` | `localhost` | Database host |
| `MURDOCK_DB_PORT` | `0` | `0` uses the backend default (27017 / 5432) |
| `MURDOCK_DB_NAME` | `murdock` | Database name |
| `MURDOCK_DB_AUTH_USER` | `murdock` | Database user |
| `MURDOCK_DB_AUTH_PASSWORD` | `hunter2` | Database password |

The upstream compose file uses `MONGODB_BD_DATA_DIR` (note the typo) for the
MongoDB data directory.

## GitHub

| Variable | Required | Description |
| --- | --- | --- |
| `MURDOCK_GITHUB_APP_CLIENT_ID` | yes | GitHub OAuth app client ID |
| `MURDOCK_GITHUB_APP_CLIENT_SECRET` | yes | GitHub OAuth app client secret |
| `GITHUB_REPO` | yes | Repository (`org/name`) this instance serves |
| `GITHUB_WEBHOOK_SECRET` | yes | HMAC secret for `/github/webhook` |
| `GITHUB_API_TOKEN` | yes | Token for statuses, comments, and content reads |

## CI policy

| Variable | Default | Description |
| --- | --- | --- |
| `CI_READY_LABEL` | `CI: ready for build` | Label required to start a PR job |
| `CI_FASTTRACK_LABELS` | `["CI: skip compile test","Process: release backport"]` | Labels that mark a PR job fasttracked |

## Notifications

| Variable | Default | Description |
| --- | --- | --- |
| `MURDOCK_NOTIFIER_PR_NOTIFIERS` | `["matrix"]` | Notifiers for PR jobs |
| `MURDOCK_NOTIFIER_BRANCH_NOTIFIERS` | `["mail","matrix"]` | Notifiers for branch pushes |
| `MURDOCK_NOTIFIER_TAG_NOTIFIERS` | `["mail","matrix"]` | Notifiers for tag pushes |
| `MURDOCK_NOTIFIER_COMMIT_NOTIFIERS` | `["matrix"]` | Notifiers for other commits |
| `MURDOCK_NOTIFIER_MAIL_RECIPIENTS` | `[]` | Email recipients |
| `MURDOCK_NOTIFIER_MAIL_SERVER` | `localhost` | SMTP server |
| `MURDOCK_NOTIFIER_MAIL_PORT` | `25` | SMTP port |
| `MURDOCK_NOTIFIER_MAIL_USE_TLS` | `true` | Use STARTTLS |
| `MURDOCK_NOTIFIER_MAIL_USERNAME` | `""` | SMTP username |
| `MURDOCK_NOTIFIER_MAIL_PASSWORD` | `""` | SMTP password |
| `MURDOCK_NOTIFIER_MATRIX_ROOM` | `""` | Matrix room ID (`!...:matrix.org`) |
| `MURDOCK_NOTIFIER_MATRIX_TOKEN` | `""` | Matrix access token |

## Deployment-only (compose / frontend)

These are used by the upstream Docker Compose stack or the UI, not by the Python
configuration module:

| Variable | Example | Description |
| --- | --- | --- |
| `COMPOSE_PROJECT_NAME` | `default` | Compose project / container name suffix |
| `MURDOCK_PORT` | `8000` | Host port for the proxy/API |
| `MURDOCK_API_PORT` | `8001` | Alternative API port in some setups |
| `MURDOCK_WS_URL` | `ws://localhost:8000/ws/status` | Frontend WebSocket URL |
| `MURDOCK_DOCKER_NETWORK` | `default` | Docker network for compose services |
| `MURDOCK_DOCKER_GID` | `130` | Host Docker group GID |
| `MURDOCK_HTML_DIR` | `./murdock-html` | Frontend source directory |
| `UVICORN_LOG_LEVEL` | `info` | Compose-level uvicorn log level |

:::note
The upstream `docker-compose.yml` contains `MURCOCK_CANCEL_ON_UPDATE` (typo).
The server reads `MURDOCK_CANCEL_ON_UPDATE`.
:::
