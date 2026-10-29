---
title: Manual jobs and badges
description: Start jobs on branches, tags, and commits, fetch the latest job, and embed badges.
---

Manual jobs require a GitHub OAuth token with `push` permission on
`GITHUB_REPO`. The token is sent raw in the `authorization` header.

All manual-job endpoints accept:

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `env` | object | `null` | Extra environment variables for the job |
| `fasttrack` | boolean | `false` | Put the job on the fasttrack queue when workers are busy |

## `POST /job/branch`

```http
POST /job/branch
Authorization: <token>
Content-Type: application/json

{"branch": "master", "env": {"BOARD": "native64"}, "fasttrack": false}
```

Murdock resolves the branch head, loads `.murdock.yml`, and schedules the job.
The job ref is `refs/heads/<branch>`.

| Status | Body |
| --- | --- |
| `200` | New `JobModel` |
| `401` | `{"detail":"Missing push permissions"}` |
| `404` | `{"detail":"No matching branch found"}` |
| `422` | Missing/invalid `branch` |

## `POST /job/tag`

```http
POST /job/tag
Authorization: <token>
Content-Type: application/json

{"tag": "2026.10", "fasttrack": true}
```

The job ref is `refs/tags/<tag>`.

| Status | Body |
| --- | --- |
| `200` | New `JobModel` |
| `404` | `{"detail":"No matching tag found"}` |

## `POST /job/commit`

```http
POST /job/commit
Authorization: <token>
Content-Type: application/json

{"sha": "0123456789abcdef0123456789abcdef01234567"}
```

The ref is the literal string `Commit <sha>`. Murdock uses the commit SHA is used for all
metadata. This is the only manual job that does not produce a `refs/...` value.

| Status | Body |
| --- | --- |
| `200` | New `JobModel` |
| `404` | `{"detail":"No matching commit found"}` |

## Latest-job convenience endpoints

These return the most recent job (by creation time) matching the key, with a
database limit of 1.

| Request | Meaning |
| --- | --- |
| `GET /job/branch/{branch}` | Last job for `refs/heads/<branch>` |
| `GET /job/tag/{tag}` | Last job for `refs/tags/<tag>` |
| `GET /job/commit/{sha}` | Last job with `commit.sha == sha` |
| `GET /job/pr/{prnum}` | Last job for PR number |

```bash
curl http://localhost:8000/job/branch/master
curl http://localhost:8000/job/pr/1234
```

If no job matches:

```http
404 {"detail":"No matching job found for branch 'master'"}
```

(commit/tag/PR variants use the corresponding key in the message.)

## Branch badge

```http
GET /job/branch/{branch}/badge
```

Returns an SVG badge for the last job of the branch, considering only states
`running`, `errored`, and `passed`.

- Content type: `image/svg+xml`
- `ETag`: the job UID
- `Cache-Control: no-cache`
- Colors: passed green, errored red, running orange
- `404` if no matching job exists

```html
<img src="https://ci.example.org/job/branch/master/badge" alt="Murdock status">
```

The badge is rendered from `murdock/templates/badge.svg.j2`.
