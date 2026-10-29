---
title: Jobs
description: List, filter, and prune job history with GET and DELETE /jobs.
---

## `GET /jobs`

Returns queued jobs, running jobs, and finished jobs from the database. The
response is a JSON array of
[`JobModel`](/api/models/#jobmodel) objects.

```http
GET /jobs?states=passed+errored&limit=10
```

### Query parameters

| Name | Type | Default | Meaning |
| --- | --- | --- | --- |
| `limit` | integer | `25` | Maximum finished jobs from the database |
| `uid` | string | None | Exact job UID |
| `is_pr` | boolean | None | With/without PR info (`prinfo` exists) |
| `is_branch` | boolean | None | Ref starts with `refs/heads/` |
| `is_tag` | boolean | None | Ref starts with `refs/tags/` |
| `states` | string | None | Space-separated job states |
| `prnum` | integer | None | PR number |
| `prstates` | string | None | Space-separated PR states (`open`, `closed`) |
| `branch` | string | None | Branch name (shorthand for `refs/heads/<branch>`) |
| `tag` | string | None | Tag name (shorthand for `refs/tags/<tag>`) |
| `ref` | string | None | Full ref, e.g. `refs/heads/master` |
| `sha` | string | None | Commit SHA |
| `tree` | string | None | Commit tree SHA |
| `author` | string | None | Commit author (GitHub login or name) |
| `after` | date | None | Created on/after `YYYY-MM-DD` |
| `before` | date | None | Created on/before `YYYY-MM-DD` (whole day) |

Unknown query parameters are ignored.

### Semantics

- `states` is matched against the job state: `queued`, `running`, `passed`,
  `errored`, `stopped`.
- `prstates` is matched against `prinfo.state` as reported by GitHub.
- `branch`/`tag`/`ref` are mutually overlapping filters. Murdock intersects them.
- `limit` only limits the database portion. If 100 jobs are running, all 100 are
  returned regardless of `limit`.
- Queued jobs are returned before running jobs, and both before history. History
  is sorted by `creation_time` descending.

### Examples

All jobs:

```bash
curl http://localhost:8000/jobs
```

Only failed jobs:

```bash
curl 'http://localhost:8000/jobs?states=errored&limit=50'
```

Jobs for one PR:

```bash
curl 'http://localhost:8000/jobs?prnum=1234&is_pr=true'
```

Merge-queue branch jobs:

```bash
curl 'http://localhost:8000/jobs?is_branch=true&branch=gh-readonly-queue/master/12345'
```

Jobs created in a date range:

```bash
curl 'http://localhost:8000/jobs?after=2026-01-01&before=2026-01-31'
```

### Response

```json
[
  {
    "uid": "e3b0c44298fc1c149afbf4c8996fb924",
    "commit": {
      "sha": "0123456789abcdef",
      "tree": "abcdef0123456789",
      "message": "tests/sys/shell: fix thing",
      "author": "contributor"
    },
    "ref": "refs/heads/master",
    "creation_time": 1760000000.0,
    "start_time": 1760000003.0,
    "state": "passed",
    "runtime": 123.4,
    "trigger": "push",
    "triggered_by": "contributor",
    "output_text_url": "https://ci.example.org/results/e3b0.../output.txt",
    "artifacts": ["output.txt"],
    "env": {"CI_JOB_UID": "e3b0...", "CI_BUILD_BRANCH": "master"}
  }
]
```

## `DELETE /jobs`

Deletes finished jobs created before a date, including their work
directories. Requires a GitHub OAuth token with `admin` permission.

```http
DELETE /jobs?before=2026-01-01
Authorization: <admin token>
```

| Parameter | Type | Required | Meaning |
| --- | --- | --- | --- |
| `before` | date | yes | Remove jobs created before this date (whole day included) |

The response is the list of removed jobs.

```json
[
  {
    "uid": "...",
    "commit": {"sha": "...", "tree": "...", "message": "...", "author": "..."},
    "creation_time": 1750000000.0,
    "state": "passed"
  }
]
```

Errors:

- `401 {"detail":"Missing admin permissions"}`,
- `422` if `before` is missing or not a date.

:::caution
There is no soft delete. The job metadata and its work directory are removed.
:::
