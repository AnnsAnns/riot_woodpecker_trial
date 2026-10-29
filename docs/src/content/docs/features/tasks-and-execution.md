---
title: Tasks and execution
description: Script mode, Docker mode, environment, output streaming, and artifacts.
---

A job executes one or more tasks sequentially in its own work directory. A
task is either a script run directly by the API process or a Docker container
spawned by the API.

## Script mode

When `MURDOCK_RUN_IN_DOCKER=0`:

```text
command = $MURDOCK_SCRIPTS_DIR/$MURDOCK_SCRIPT_NAME
cwd     = $MURDOCK_WORK_DIR/<job uid>
env     = job environment + task env
```

The script must be executable. Murdock uses
`asyncio.create_subprocess_exec`, not a shell, so shell syntax belongs inside
the script. The default script name is `run.sh`.

Stopping a script-mode task sends `SIGINT` to the whole process group. Murdock
waits up to five seconds for it to exit. It logs a warning if the process does not exit. It does not send `SIGKILL`.

## Docker mode

When `MURDOCK_RUN_IN_DOCKER=1`, Murdock runs:

```sh
/usr/bin/docker run --rm --stop-signal SIGINT \
  --cpus=<MURDOCK_DOCKER_CPU_LIMIT> \
  --memory=<MURDOCK_DOCKER_MEM_LIMIT> \
  --network container:murdock-api-<MURDOCK_PROJECT> \
  --user <MURDOCK_USER_UID>:<MURDOCK_USER_GID> \
  --env "KEY=VALUE" ... \
  --volume <host_work_dir>/<uid>:/murdock \
  --name murdock-job-<uid> \
  --workdir /murdock \
  <image> <command>
```

Key points:

- `image` comes from the task, falling back to
  `MURDOCK_DOCKER_DEFAULT_TASK_IMAGE` (default `ubuntu:latest`).
- `command` is split with `shlex` and appended after the image. If omitted, the
  image's default command runs.
- The job directory is mounted at `/murdock`. The host side is
  `MURDOCK_HOST_WORK_DIR/<uid>`, which must match the path where the API's
  `MURDOCK_WORK_DIR` is visible on the host. This matters when Murdock
  itself runs in a container.
- Additional volumes come from `MURDOCK_DOCKER_VOLUMES` (a JSON/YAML map of
  host path to container path).
- The container joins the API container's network namespace
  (`container:murdock-api-<project>`), so it can reach the API and other
  services on that network.
- Stopping sends `docker stop --time 5`.

## Multiple tasks

Tasks run in order. With more than one task, Murdock writes separators to the job
output:

```text
-- Running 'build' task --
...
-- 'build' task completed (passed) --
```

Execution stops early if a task returns `stopped` or `errored`. The overall job
state is the state of the last executed task.

## Output

- Stdout and stderr are merged.
- Lines are streamed to WebSocket clients as `{"cmd":"output","uid":...,"line":...}`.
- Carriage returns are replaced with newlines.
- The complete output is written to `$MURDOCK_WORK_DIR/<uid>/output.txt` and
  exposed through `output_text_url`.

## Result and artifacts

A task result is:

- `passed` if the process exits with status 0,
- `stopped` if it was stopped by Murdock,
- `errored` otherwise.

After all tasks, Murdock checks each path in `.murdock.yml` → `artifacts`. Paths
that exist are added to the job's `artifacts` list. The job itself does not
upload anything. Artifacts and output are served from the work directory by the
`/results` static route.

## Environment

The full job environment is documented in
[Job environment](/reference/job-environment/). The important pieces:

- `CI_JOB_UID`, `CI_JOB_TOKEN`, `CI_BASE_URL`,
- PR variables such as `CI_PULL_NR`, `CI_PULL_COMMIT`, `CI_BASE_BRANCH`,
  `CI_BASE_COMMIT`, `CI_PULL_LABELS`, `CI_MERGE_COMMIT`,
- push variables such as `CI_BUILD_COMMIT`, `CI_BUILD_REF`, `CI_BUILD_BRANCH`,
  `CI_BUILD_TAG`,
- project and configuration variables such as `CI_MURDOCK_PROJECT`, `CI_SCRIPTS_DIR`.

`CI_JOB_TOKEN` and `CI_SCRIPTS_DIR` are stripped from the public `env` field in
API responses.
