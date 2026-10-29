---
title: Security
description: Authentication, job tokens, webhook signatures, permissions, and secret handling.
---

Murdock has a deliberately small security model: it trusts GitHub as the
identity provider and uses a separate per-job token for status updates.

## API authentication

Read endpoints are public. Write endpoints require a raw GitHub OAuth token in
the `authorization` header:

```http
Authorization: <github oauth token>
```

Murdock checks the token against the configured repository:

```http
GET https://api.github.com/repos/<GITHUB_REPO>
Authorization: token <token>
```

| Endpoint | Required GitHub permission |
| --- | --- |
| `POST /job/branch` | `push` |
| `POST /job/tag` | `push` |
| `POST /job/commit` | `push` |
| `POST /job/{uid}` (restart) | `push` |
| `DELETE /job/{uid}` | `push` |
| `DELETE /jobs?before=...` | `admin` |

Failures return `401` with `Missing push permissions` or
`Missing admin permissions`. The token is not stored except in the request.

## Job status token

Every job receives a random URL-safe token as `CI_JOB_TOKEN`. To update progress,
the job sends:

```http
PUT /job/{uid}/status
Authorization: <CI_JOB_TOKEN>
Content-Type: application/json
```

The token must match exactly. Missing or wrong tokens return `400`:

- `No job running with uid <uid>` if the job is not in the running pool,
- `Job token is missing`,
- `Invalid Job token`.

The token is removed from the public `env` field. `CI_SCRIPTS_DIR` is also
removed. User-supplied `user_env` is returned as-is, so do not put secrets there.

## Webhook signature

`/github/webhook` requires a valid GitHub HMAC (hash-based message authentication code):

```text
X-Hub-Signature-256: sha256=<HMAC-SHA256(GITHUB_WEBHOOK_SECRET, raw body)>
```

The comparison is constant-time. Invalid signatures are rejected before the
payload is parsed.

## Repository allowlist

`GITHUB_REPO` is the single repository this instance serves. Webhooks from other
repositories are rejected with `Invalid repo`. Manual jobs and API permission
checks always use the same repository.

## CORS

CORS is fully open:

```python
allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
```

This is convenient for a public read-only API, but it means any website can call
the API from a browser. Write endpoints still require a valid GitHub token.

## Secret handling

- GitHub client secrets, API tokens, and webhook secrets come from the
  environment / `.env` file.
- `.murdock.yml` is fetched from the repository and is public to anyone who can
  read the repository. Never put secrets in it.
- `MURDOCK_CUSTOM_ENV` and `.murdock.yml` → `env` are visible to job processes
  and (except the two unsafe variables) returned in the job model.
- The mail notifier logs authentication and connection errors but not the
  password.

## Hardening checklist

- Terminate TLS in a reverse proxy. Do not expose the API over plain HTTP.
- Keep `GITHUB_WEBHOOK_SECRET` and `GITHUB_API_TOKEN` out of source control.
- Restrict the Docker socket if Docker task mode is enabled.
- Set `MURDOCK_ENABLE_PR_COMMENT=0` and `MURDOCK_ENABLE_COMMIT_STATUS=0` while
  testing against a real repository.
- Prune job history and work directories to avoid unbounded disk use.
