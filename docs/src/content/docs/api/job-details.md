---
title: Job details and status
description: Get, restart, remove jobs, and update a running job's progress.
---

## `GET /job/{uid}`

Returns one [`JobModel`](/api/models/#jobmodel), searching queued, running, and
finished jobs.

```http
GET /job/e3b0c44298fc1c149afbf4c8996fb924
```

```bash
curl http://localhost:8000/job/e3b0c44298fc1c149afbf4c8996fb924
```

If no job matches:

```http
404 {"detail":"No job matching uid 'e3b0...' found"}
```

## Restart a job

Creates a new job from a finished job's commit, ref/PR, and user environment.
Murdock reloads `.murdock.yml`, sets `trigger` to `api (restart)`, and schedules
the new job. Requires `push` permission.

```http
POST /job/e3b0c44298fc1c149afbf4c8996fb924
Authorization: <github oauth token>
```

The response is the new `JobModel`. If the job cannot be found:

```http
404 {"detail":"Cannot restart job 'e3b0...'"}
```

Only jobs present in the database (finished jobs) can be restarted. The endpoint does not accept queued and
running jobs are not accepted by this endpoint.

## Remove, cancel, or stop a job

Requires `push` permission. Behavior depends on where the job is:

| Job location | Effect |
| --- | --- |
| Queued | Cancels it and removes it from the queue |
| Running | Stops its current task |
| Database | Deletes the metadata and its work directory |

```http
DELETE /job/e3b0c44298fc1c149afbf4c8996fb924
Authorization: <github oauth token>
```

The response is the affected `JobModel`. If nothing matches:

```http
404 {"detail":"No job with uid 'e3b0...' found"}
```

## Update job progress

This endpoint is called by the job itself, not by a user. It requires the
job's `CI_JOB_TOKEN` in the `Authorization` header.

```http
PUT /job/e3b0c44298fc1c149afbf4c8996fb924/status
Authorization: <CI_JOB_TOKEN>
Content-Type: application/json
```

```json
{
  "status": {
    "status": "working",
    "total": 123,
    "passed": 80,
    "failed": 2,
    "eta": "00:12:31",
    "failed_builds": [
      {
        "application": "tests/sys/shell",
        "target": "native64",
        "toolchain": "llvm",
        "worker": "worker-1",
        "runtime": 12.3
      }
    ]
  }
}
```

The body is free-form. Murdock only requires a truthy `status` object. Extra
top-level fields are echoed to WebSocket clients.

### Validation order

1. The job must be in the running pool:
   `400 {"detail":"No job running with uid <uid>"}`.
2. An `Authorization` header must be present:
   `400 {"detail":"Job token is missing"}`.
3. The header must equal the job token exactly:
   `400 {"detail":"Invalid Job token"}`.
4. `handle_job_status_data` must find the job:
   `404 {"detail":"No job with uid '<uid>' found"}`.

On success it returns the updated `JobModel`.

### Failfast

If the job's `.murdock.yml` has `failfast: true` and the status object contains
`failed_jobs`, `failed_builds`, or `failed_tests`, Murdock stops the job and
sets its state to `errored`.

### WebSocket broadcast

The server broadcasts:

```json
{
  "cmd": "status",
  "uid": "e3b0...",
  "status": {
    "status": "working",
    "total": 123,
    "passed": 80,
    "failed": 2
  }
}
```

Any additional top-level fields from the request body are included in the
broadcast as well.

## Typical job script usage

```sh
curl -sS -X PUT "$CI_BASE_URL/job/$CI_JOB_UID/status" \
  -H "Content-Type: application/json" \
  -H "Authorization: $CI_JOB_TOKEN" \
  -d '{"status":{"status":"working","total":100,"passed":42,"failed":0}}'
```
