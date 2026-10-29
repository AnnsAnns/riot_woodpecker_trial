---
title: Triggers and gates
description: Pull requests, pushes, manual jobs, labels, skip keywords, and ref filters.
---

Murdock accepts jobs from GitHub webhooks and from the manual-job API. Every
source passes through the same policy checks before a job is scheduled.

## Pull requests

Murdock handles these `pull_request` actions:

`edited`, `labeled`, `unlabeled`, `synchronize`, `created`, `closed`, `opened`,
`reopened`.

`/github/webhook` also rejects a webhook when:

- the HMAC signature is invalid,
- the event type is not in `MURDOCK_ACCEPTED_EVENTS` (default `push` and
  `pull_request`),
- the repository `full_name` does not match `GITHUB_REPO`.

### Ready label

A PR does not build automatically. The label configured by `CI_READY_LABEL`
(default `CI: ready for build`) must be present.

| Event | Behavior |
| --- | --- |
| `opened` | Updates matching jobs. Schedules only if the ready label is already present through the later `labeled` event. |
| `labeled` | Schedules only when the added label is the ready label. Skips the job if a job for the PR is already queued. |
| `synchronize` | Schedules a new job if the ready label is present. |
| `reopened` | Schedules if the ready label is present. |
| `edited` | Updates PR metadata (title/labels/state) but does not schedule. |
| `unlabeled` | Updates metadata and disables matching jobs if the ready label was removed. |
| `closed` | Cancels queued jobs and stops running jobs for the PR. It does not create a new job. |

If the ready label is missing, Murdock also sets a pending commit status whose
description is `"<label>" label not set` and cancels any matching queued/running
jobs.

### PR metadata updates

For every PR event, Murdock updates the title, labels, state, and merged flag of
queued, running, and historical jobs for that PR. This keeps the UI accurate when
a PR is edited after a build.

## Pushes

For `push` events, Murdock extracts the branch or tag name from `ref` and checks
it against `.murdock.yml`:

```yaml
push:
  branches:
    - '^staging$'
    - '^trying$'
    - '^gh-readonly-queue/'
  tags:
    - '^v[0-9]+\.[0-9]+$'
```

Rules are evaluated as:

1. `*` matches everything,
2. an exact string match, or
3. a Python regular expression match (`re.match`).

An empty list means no branch/tag is accepted. Tags and branches are checked
separately.

If the event's `after` commit is all zeros, the ref was deleted. Murdock
invokes its cancel and stop helpers for matching jobs instead of scheduling a
new one.

:::caution
The current server code calls the queued-job cancel helper for running jobs and
the running-job stop helper for queued jobs. The intent is to cancel queued jobs
and stop running jobs, but the order is swapped. Test this path on your Murdock
version.
:::

## Skip keywords

The per-repository `.murdock.yml` can define:

```yaml
commit:
  skip_keywords: ["ci_skip", "murdock_skip", "[ci skip]"]
```

If any keyword appears in the commit message, the job is not scheduled and a
pending commit status with description `The job was skipped.` is set. This
applies to PR, push, and manual jobs because they all pass through
`handle_skip_job`.

## Manual jobs

Manual jobs require a GitHub OAuth token with `push` permission on
`GITHUB_REPO`.

| Endpoint | Creates a job for |
| --- | --- |
| `POST /job/branch` | the head of a branch |
| `POST /job/tag` | a tag |
| `POST /job/commit` | an explicit commit SHA |

All three accept optional `env` and `fasttrack`. The trigger is
`api (manual)`. Manual jobs still load `.murdock.yml`, honour skip keywords, and
cancel matching work when `cancel_on_update` is enabled.

## Restart

`POST /job/{uid}` restarts a finished job. The new job uses the original commit,
ref/PR, and user environment, and the trigger is `api (restart)`.

## RIOT-specific gates

RIOT adds another layer inside its own `.murdock` script. These are not server
features, but they control which jobs RIOT generates:

- `CI: ready for build`: server gate described above,
- `CI: full build`: build every application on every supported board,
- `CI: skip compile test`: skip compile jobs,
- `CI: run tests`: enable hardware-in-the-loop tests,
- `CI: no fast fail`: raise the abort limit instead of stopping after the first
  failure,
- `CI: disable test cache`: bypass the Redis test-result cache,
- `gh-readonly-queue/` branches: always full builds,
- `NIGHTLY=1`: nightly full builds and tests.

See [RIOT CI](/features/riot-ci/) for the complete flow.
