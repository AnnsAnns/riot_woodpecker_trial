---
title: GitHub integration
description: Webhooks, commit statuses, pull-request comments, OAuth, and commit metadata.
---

Murdock is tightly coupled to GitHub. It accepts events from one repository,
reads commit/branch/tag metadata, writes commit statuses and PR comments, and
checks OAuth tokens against repository permissions.

## Webhook

`POST /github/webhook` is intentionally excluded from the OpenAPI schema.

- Signature: `X-Hub-Signature-256: sha256=<hex>`, computed as
  `HMAC-SHA256(GITHUB_WEBHOOK_SECRET, raw_body)`.
- Event type: `X-Github-Event`, must be in `MURDOCK_ACCEPTED_EVENTS`
  (default `push`, `pull_request`).
- Repository: `event.repository.full_name` must equal `GITHUB_REPO` when that
  setting is non-empty.
- Invalid signature → `400 {"detail":"Invalid event signature"}`.
- Unsupported event → `400 {"detail":"Unsupported event"}`.
- Handler errors returned as a string become `400 {"detail":"..."}`.

See [Webhooks API](/api/webhooks/) for the exact request contract.

## Commit statuses

Murdock writes GitHub statuses with:

```json
{
  "state": "pending | success | failure",
  "context": "Murdock",
  "description": "The job has been queued",
  "target_url": "https://ci.example.org/details/<uid>"
}
```

`context` is `MURDOCK_COMMIT_STATUS_CONTEXT` (default `Murdock`). Typical
descriptions:

| Moment | State | Description |
| --- | --- | --- |
| Queued | `pending` | `The job has been queued` |
| Started | `pending` | `The job has started` |
| Passed | `success` | `The job succeeded. runtime: 12m34s` |
| Errored | `failure` | `The job failed. runtime: 12m34s` |
| Stopped | `pending` | `Stopped` |
| Skipped | `pending` | `The job was skipped.` |
| Missing ready label | `pending` | `"CI: ready for build" label not set` |

Global writes can be disabled with `MURDOCK_ENABLE_COMMIT_STATUS=0`.

:::note
The `target_url` points to `MURDOCK_BASE_URL/details/<uid>`, which is a frontend
route. The API itself does not serve `/details`. The web UI does.
:::

## Pull-request comments

If `.murdock.yml` enables PR comments, Murdock renders a Markdown comment from
`murdock/templates/comment.md.j2`:

```markdown
### Murdock results

:heavy_check_mark: [PASSED](https://ci.example.org/details/<uid>)

<sha> <first line of commit message>

| Success | Failures | Total | Runtime |
| :-----: | :------: | :---: | :-----: |
| 120 | 3 | 123 | 18m02s |

<details><summary><strong>Build failures (3)</strong></summary>
...
</details>
```

The template also renders failed test tables and artifact links. It uses
`job.status` fields supplied by the job script:

- `status`, `total`, `passed`, `failed`, `eta`,
- `failed_jobs` (list of `{name, href?}`),
- `failed_builds` / `failed_tests` (lists with `application`, `target`,
  `toolchain`, `worker`, `runtime`).

### Sticky comments

With `sticky_comment: true`, Murdock searches the issue comments (up to 10
pages) for a comment whose first line is `### Murdock results` and updates it.
Otherwise it posts a new comment.

### Artifact links and footer

`comment_artifacts` links artifacts that exist in the job's `artifacts` list:

```yaml
pr:
  comment_artifacts:
    - name: doc-preview/
      readable_name: Documentation preview
```

`comment_footer` is appended verbatim. PR comments are also gated globally by
`MURDOCK_ENABLE_PR_COMMENT`.

## OAuth and permissions

Write endpoints take a raw GitHub OAuth token in the `authorization` header
(not `Bearer ...`). Murdock checks it by calling:

```http
GET https://api.github.com/repos/<GITHUB_REPO>
Authorization: token <token>
```

and checking `permissions.push` or `permissions.admin`. A failed check returns
`401` with `Missing push permissions` / `Missing admin permissions`.

| Level | Used by |
| --- | --- |
| push | manual jobs, restart, delete job, job status updates (separate job token) |
| admin | delete finished jobs in bulk |

The browser OAuth flow uses `GET /github/authenticate/{code}`, which exchanges a
code for a token and returns `{"token": "..."}`. This endpoint lets a static single-page app (SPA)
avoid exposing the OAuth client secret. It is excluded from the OpenAPI schema.

## Repository metadata

Murdock reads from the GitHub REST API:

- commits (`/commits/{sha}`) for SHA, tree, message, author,
- branches (`/branches/{name}`) for manual branch jobs,
- tags (`/git/refs/tags/{tag}`) for manual tag jobs,
- the current user (`/user`) to record `triggered_by`,
- `.murdock.yml` from `/contents/.murdock.yml?ref=<sha>`.

If a lookup fails, the corresponding manual job returns `404` (“No matching
branch/tag/commit found”). A missing or invalid `.murdock.yml` silently falls
back to defaults.

## One repository per instance

`GITHUB_REPO` is a single repository (`org/name`). A Murdock instance serves one
repository. Use separate instances or projects for multiple repositories.
