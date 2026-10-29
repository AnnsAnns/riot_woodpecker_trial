---
title: Realtime updates and metrics
description: The status WebSocket protocol and Prometheus metrics exposed by Murdock.
---

Murdock provides live job updates over a WebSocket and exposes Prometheus
metrics. The web UI uses the WebSocket to avoid polling and reload the job list
when state changes.

## WebSocket

Connect to:

```text
ws://<host>/ws/status
```

The server accepts the connection and keeps it open. It does not send pings and
does not require an initial message. The read loop waits for client text and
does not reply to it.

The server sends JSON text messages:

| `cmd` | Payload | Meaning |
| --- | --- | --- |
| `reload` | `{"cmd":"reload"}` | Queued/running/finished jobs changed. Refetch `/jobs` |
| `status` | `{"cmd":"status","uid":"...","status":{...}}` | A job reported progress. Update its status |
| `output` | `{"cmd":"output","uid":"...","line":"..."}` | A new output line |

Examples:

```json
{"cmd":"reload"}
```

```json
{"cmd":"status","uid":"6f1c...","status":{"status":"working","total":123,"passed":80,"failed":2,"eta":"00:12:31"}}
```

```json
{"cmd":"output","uid":"6f1c...","line":"-- building tests/sys/shell\n"}
```

The WebSocket is broadcast-only. It has no authentication and no per-job
subscription. Every connected client receives every message for the instance.

## Metrics

`prometheus-fastapi-instrumentator` exposes the standard HTTP metrics and the
custom Murdock metrics at `/metrics` (excluded from the OpenAPI schema).

| Metric | Type | Labels | Meaning |
| --- | --- | --- | --- |
| `murdock_job_queued` | counter | None | Jobs added to the queue |
| `murdock_job_start` | counter | None | Jobs started |
| `murdock_job_result` | counter | `status` | Finished jobs (`passed`, `errored`, `stopped`, `canceled`) |
| `murdock_task_result` | counter | `status` | Task results (`passed`, `failed`) |
| `murdock_webhook_push_events` | counter | `repository`, `push` | Push webhook events (`commit` or `tag`) |
| `murdock_webhook_pull_events` | counter | `repository`, `action` | PR webhook events by action |
| `murdock_build_info` | info | `worker` | Current worker/job metadata |
| `murdock_jobs_running` | gauge | None | Jobs currently running |
| `murdock_num_workers` | gauge | None | Configured worker count |
| `murdock_websockets_active` | gauge | None | Connected WebSocket clients |

`murdock_build_info` is set while a worker processes a job and removed when the
job finishes. Its info fields are `uuid`, `commit`, `title`, `creation_time`
(milliseconds), `fasttracked`, and `state`.

## Scraping

```yaml
scrape_configs:
  - job_name: murdock
    static_configs:
      - targets: ['murdock:8000']
```

The legacy worker fleet forwards worker and Redis metrics through Vector to the
control node. The modern API does not require it.
