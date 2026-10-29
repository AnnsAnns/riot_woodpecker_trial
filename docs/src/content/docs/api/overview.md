---
title: API overview
description: Base URL, authentication, errors, and the complete endpoint inventory.
---

The Murdock API is a FastAPI application. The canonical schema is served by the
running instance at `/openapi.json`. This guide vendors a snapshot and adds
hand-written pages for the routes that are intentionally hidden from the schema.

## Base URL

```text
http://<host>:8000
```

All examples use `http://localhost:8000`.

## Content types

- Requests with a body use `application/json`.
- Responses are `application/json`, except the branch badge
  (`image/svg+xml`) and `/results/...` static files.
- `JobModel` responses use `response_model_exclude_none=True`, so `null` fields
  are omitted rather than serialized as `null`.

## Authentication

Read endpoints are public. Write endpoints use a raw GitHub OAuth token:

```http
Authorization: <github oauth token>
```

This is not a Bearer token. Murdock checks the token against
`GITHUB_REPO` for `push` or `admin` permission. The job status endpoint uses a
different, per-job token (`CI_JOB_TOKEN`) in the same header.

| Scheme | Header | Used by |
| --- | --- | --- |
| GitHub OAuth Token | `authorization` | manual jobs, restart, delete, bulk delete |
| Job token | `Authorization` | `PUT /job/{uid}/status` |
| Webhook HMAC | `X-Hub-Signature-256` | `POST /github/webhook` |

## Endpoint inventory

### Documented in OpenAPI

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/jobs` | List/filter jobs |
| DELETE | `/jobs` | Delete finished jobs before a date (admin) |
| GET | `/job/{uid}` | Job details |
| POST | `/job/{uid}` | Restart a finished job (push) |
| DELETE | `/job/{uid}` | Remove/cancel/stop a job (push) |
| PUT | `/job/{uid}/status` | Update progress (job token) |
| POST | `/job/branch` | Start a manual branch job (push) |
| GET | `/job/branch/{branch}` | Last job for a branch |
| GET | `/job/branch/{branch}/badge` | SVG badge for a branch |
| POST | `/job/tag` | Start a manual tag job (push) |
| GET | `/job/tag/{tag}` | Last job for a tag |
| POST | `/job/commit` | Start a manual commit job (push) |
| GET | `/job/commit/{sha}` | Last job for a commit |
| GET | `/job/pr/{prnum}` | Last job for a PR number |

### Hidden from OpenAPI

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/github/webhook` | GitHub webhook receiver |
| GET | `/github/authenticate/{code}` | OAuth code → token exchange |
| GET | `/ws/status` | Live status WebSocket |
| GET | `/results/{path}` | Static job output/artifacts |
| GET | `/metrics` | Prometheus metrics |
| GET | `/api` | Swagger UI |
| GET | `/openapi.json` | OpenAPI schema |

There is no `/health` endpoint. A request returns `404`. Use `/jobs` or the
root UI as a liveness check.

## Errors

Murdock uses standard FastAPI error responses:

```json
{"detail": "No job matching uid 'abc' found"}
```

| Status | When |
| --- | --- |
| `400` | Invalid webhook signature, unsupported event, bad job token, handler error |
| `401` | Missing GitHub `push`/`admin` permission |
| `404` | Unknown job, branch, tag, commit, PR, or badge |
| `422` | Request body/query validation error (FastAPI) |
| `500` | Unhandled server error |

`422` responses have the FastAPI validation shape:

```json
{
  "detail": [
    {
      "loc": ["body", "branch"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Conventions

- Space-separated lists: `states` and `prstates` are split on spaces:
  `?states=queued+running+passed+errored+stopped`.
- Dates: `after` and `before` use `YYYY-MM-DD`. `before` includes the whole
  day (23:59:59.999).
- Refs: `branch` and `tag` are shorthand for `refs/heads/<branch>` and
  `refs/tags/<tag>`. `ref` takes a full ref.
- Limits: `limit` defaults to 25 and is applied to the database query. Queued
  and running jobs are always returned in full.
- Ordering: queued jobs are returned first, then running jobs, then finished
  jobs newest-first.

## Generated operation pages

The [OpenAPI Operations](/api/openapi/) section is generated from
`src/assets/openapi.json` and contains request and response schemas and code
snippets for each documented route. The hand-written pages add semantics,
examples, and the hidden routes. The snapshot keeps the API shape and corrects a
few spelling mistakes in upstream field titles.
