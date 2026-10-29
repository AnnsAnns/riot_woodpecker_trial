---
title: Jobs and scheduling
description: Job states, queues, workers, fasttracking, failfast, cancellation, restart, and history.
---

A Murdock job represents one CI run for a commit. It owns its environment,
work directory, output, status, artifacts, and a unique UID (a UUID, universally
unique identifier, in hex form). Jobs are created from forge events or the
manual-job API. For RIOT, one Murdock job can contain many build and test
subjobs. See [RIOT job aggregation](/features/riot-job-aggregation/).

## States

| State | Meaning |
| --- | --- |
| `queued` | Created and waiting for a worker |
| `running` | A worker is executing its tasks |
| `passed` | All tasks exited successfully |
| `errored` | A task failed, the prepare/finalize step failed, or failfast stopped it |
| `stopped` | Canceled or stopped by a user/event |

Murdock also tracks a `canceled` flag internally for queued jobs that were
removed before starting. The external state remains `queued` until they are
gone. The Prometheus counter has a `canceled` label for this case.

## Queues and workers

- `MURDOCK_NUM_WORKERS` async workers consume jobs from an in-memory queue.
- Queued jobs are also kept in an in-memory list so the API can show them before
  a worker starts.
- Running jobs occupy a fixed-size pool of `MURDOCK_NUM_WORKERS` slots.
- The API serves a merged view: queued jobs first, then running jobs, then
  finished jobs from the database.
- There is no hard job timeout. A task that never exits keeps its worker busy
  until it is stopped.

## Fasttrack

A job is `fasttracked` when:

- it is a pull request whose labels include one of `CI_FASTTRACK_LABELS`
  (default: `CI: skip compile test`, `Process: release backport`), or
- a manual job sets `"fasttrack": true`.

Fasttracked jobs normally enter the same queue. If all workers are busy when
the job is queued, the job is placed on a separate fasttrack queue instead, so it
is the next job picked up when a worker becomes free. Fasttrack does not
preempt a running job.

## Cancel-on-update

`MURDOCK_CANCEL_ON_UPDATE` (default `true`) implements “latest event wins”:

- when a new job is scheduled, queued jobs for the same PR number or ref are
  canceled,
- running jobs for the same PR/ref are stopped,
- the new job is then queued.

This prevents a stale push or PR synchronisation from continuing after a newer
commit arrives.

## Failfast

Failfast is a per-repository setting (`.murdock.yml` → `failfast: true`). It is
not the same as RIOT's `CI: no fast fail` label, which is implemented in RIOT's
build script.

When enabled, Murdock watches the `status` payload sent by the job. If the
payload contains `failed_jobs`, `failed_builds`, or `failed_tests`, the job is
stopped and its state is set to `errored`.

## Stopping and restarting

- Stop a running job with `DELETE /job/{uid}`. If the job is queued it is
  canceled. If it is running, Murdock stops it. If it is already finished, Murdock deletes it
  deleted from the database. This requires push permission.
- Restart a finished job with `POST /job/{uid}`. Murdock reloads
  `.murdock.yml` for the original commit, creates a new job with the same
  commit/ref/PR/user environment, and schedules it with the trigger
  `api (restart)`. This also requires push permission.
- Stopping a job sets `stopped`. Murdock keeps the work directory is kept unless
  `MURDOCK_STORE_STOPPED_JOBS` is false.

## History and cleanup

Finished jobs are stored in MongoDB or PostgreSQL. `GET /jobs` merges live and
stored jobs, with `limit` applied to the database query. To prune history:

```http
DELETE /jobs?before=2026-01-01
Authorization: <admin GitHub OAuth token>
```

`before` is a `YYYY-MM-DD` date and includes the whole day. The endpoint removes
the jobs and their work directories, and requires GitHub `admin` permission on
the configured repository.

## Job UID and token

Every job gets two identifiers:

- `uid`: public UUID hex string used in URLs,
- `token`: a random URL-safe secret sent to the job as `CI_JOB_TOKEN`.

The token is not exposed by the API (`CI_JOB_TOKEN` and `CI_SCRIPTS_DIR` are
removed from the `env` field). It is required to update the job's status. See
[Security](/features/security/).
