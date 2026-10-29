---
title: Results, metrics, and docs
description: Static job results, Prometheus metrics, Swagger UI, and the OpenAPI schema.
---

## `/results/{path}`

`/results` serves the Murdock work directory as static files:

```python
app.mount("/results", StaticFiles(directory=GLOBAL_CONFIG.work_dir, html=True, check_dir=False))
```

Examples:

```text
GET /results/<uid>/output.txt
GET /results/<uid>/doc-preview/index.html
GET /results/<uid>/output/builds/tests_sys_shell/native64:gnu.txt
```

- `html=True` renders `index.html` for directory requests.
- `check_dir=False` means a missing work directory does not prevent startup.
- There is no authentication. Anyone who can reach the API can read job output
  and artifacts.
- The files are whatever the job wrote. Murdock does not rewrite or check
  them.

## `/metrics`

Prometheus/OpenMetrics endpoint exposed by
`prometheus-fastapi-instrumentator`. It includes HTTP request metrics and the
custom `murdock_*` metrics described in
[Realtime updates and metrics](/features/realtime-and-metrics/#metrics).

```bash
curl http://localhost:8000/metrics
```

## `/api`

Swagger UI for the documented routes. It loads the OpenAPI schema from
`/openapi.json` and the Swagger UI assets from a CDN.

```text
http://localhost:8000/api
```

## `/openapi.json`

The machine-readable OpenAPI 3.0.2 schema. This is the source used to generate
the [OpenAPI Operations](/api/openapi/) pages in this guide.

```bash
curl http://localhost:8000/openapi.json
```

## `/redoc`

Disabled (`redoc_url=None`). Use `/api` or `/openapi.json`.

## `/details/{uid}`

Not an API route. It is a frontend route used as the `target_url` of GitHub
commit statuses. The API does not serve `/details`. The deployed web UI does.

## `/health`

Not implemented. `GET /health` returns `404`. Use `/jobs`, `/openapi.json`, or
the frontend root as a liveness check.
