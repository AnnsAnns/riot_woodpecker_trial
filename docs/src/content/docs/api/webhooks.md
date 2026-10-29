---
title: Webhooks and OAuth exchange
description: The GitHub webhook receiver and the OAuth code exchange endpoint.
---

Both endpoints on this page are intentionally excluded from the OpenAPI schema.
They are part of the GitHub integration rather than the public job API.

## `POST /github/webhook`

Receives GitHub `push` and `pull_request` events.

### Headers

| Header | Required | Meaning |
| --- | --- | --- |
| `X-Hub-Signature-256` | yes | `sha256=<HMAC-SHA256(GITHUB_WEBHOOK_SECRET, raw_body)>` |
| `X-Github-Event` | yes | `push` or `pull_request` (or another accepted event) |
| `Content-Type` | yes | `application/json` (GitHub sends `application/vnd.github.v3+json`) |

### Validation

1. Compute the HMAC (hash-based message authentication code) over the raw body and compare it in constant time.
   Invalid → `400 {"detail":"Invalid event signature"}`.
2. Check `X-Github-Event` against `MURDOCK_ACCEPTED_EVENTS`
   (default `["push", "pull_request"]`).
   Unsupported → `400 {"detail":"Unsupported event"}`.
3. For PR events, check `event.repository.full_name == GITHUB_REPO`.
   Mismatch → `400 {"detail":"Invalid repo"}`.
4. Parse the JSON and dispatch to `handle_pull_request_event` or
   `handle_push_event`.
5. If the handler returns a string, it becomes `400 {"detail":"<string>"}`.
   Otherwise the response is `200`.

### Pull-request payload fields used

| Field | Used for |
| --- | --- |
| `action` | Gate: `edited`, `labeled`, `unlabeled`, `synchronize`, `created`, `closed`, `opened`, `reopened` |
| `pull_request.title` | Stored in `prinfo.title` |
| `pull_request.number` | PR number |
| `pull_request.merge_commit_sha` | `prinfo.merge_commit` / `CI_MERGE_COMMIT` |
| `pull_request.head.sha` | Commit to build |
| `pull_request.head.user.login` | PR author |
| `pull_request._links.html.href` | PR URL |
| `pull_request.base.repo.clone_url` | Base repo |
| `pull_request.base.ref` | Base branch |
| `pull_request.base.sha` | Base commit |
| `pull_request.base.repo.full_name` | Base full name |
| `pull_request.mergeable` | Mergeable flag |
| `pull_request.labels[].name` | Labels (sorted) |
| `pull_request.state` | `open` / `closed` |
| `pull_request.merged_at` | `is_merged` |
| `event.sender.login` | Triggered-by user |
| `event.label.name` | Label added/removed (for `labeled`/`unlabeled`) |

### Push payload fields used

| Field | Used for |
| --- | --- |
| `ref` | Branch or tag ref (`refs/heads/...`, `refs/tags/...`) |
| `after` | Commit SHA. All zeros means the ref was deleted |
| `repository.full_name` | Repository allowlist |
| `sender.login` | Triggered-by user |

### Example

```bash
BODY='{"zen":"...","ref":"refs/heads/master","after":"0123...","repository":{"full_name":"org/repo"},"sender":{"login":"user"}}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$GITHUB_WEBHOOK_SECRET" | sed 's/^.* //')

curl -X POST http://localhost:8000/github/webhook \
  -H "X-Github-Event: push" \
  -H "X-Hub-Signature-256: sha256=$SIG" \
  -H "Content-Type: application/json" \
  -d "$BODY"
```

## `GET /github/authenticate/{code}`

Exchanges a GitHub OAuth authorization code for an access token. This exists so a
browser SPA can complete OAuth without knowing the client secret.

```http
GET /github/authenticate/<code>
```

Murdock sends:

```http
POST https://github.com/login/oauth/access_token
Accept: application/vnd.github.v3+json

client_id=<MURDOCK_GITHUB_APP_CLIENT_ID>
client_secret=<MURDOCK_GITHUB_APP_CLIENT_SECRET>
code=<code>
```

and returns:

```json
{"token": "gho_..."}
```

Notes:

- The endpoint is excluded from the OpenAPI schema.
- It does not check or store the token. It only performs the exchange.
- A GitHub error response without `access_token` results in a server error.
- The `murfrog` UI uses this endpoint (or an external Cloudflare Worker
  gatekeeper) for its login flow.
