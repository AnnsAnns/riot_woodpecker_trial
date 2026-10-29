---
title: Data models
description: JobModel, CommitModel, PullRequestInfo, manual-job parameters, and status payloads.
---

All models are Pydantic models from `murdock/models.py`. API responses use
`response_model_exclude_none=True`, so unset fields are omitted.

## `JobModel`

| Field | Type | Description |
| --- | --- | --- |
| `uid` | string | Unique job identifier (UUID, universally unique identifier, in hex) |
| `commit` | `CommitModel` | Commit metadata |
| `ref` | string? | Full ref (`refs/heads/...`, `refs/tags/...`) or `Commit <sha>` |
| `prinfo` | `PullRequestInfo`? | PR metadata for PR jobs |
| `creation_time` | number | Unix timestamp (seconds) |
| `start_time` | number | Unix timestamp in seconds. The value is 0 if the job did not start |
| `fasttracked` | boolean? | Whether the job is fasttracked |
| `status` | object? | Free-form progress payload from the job |
| `state` | string? | `queued`, `running`, `passed`, `errored`, `stopped` |
| `output` | string? | Full output text |
| `output_text_url` | string? | URL to `output.txt` |
| `runtime` | number? | Runtime in seconds. For a running job, this value can be negative because the stop time is zero until the job finishes. |
| `trigger` | string | `push`, `pr (<action>)`, `api (manual)`, `api (restart)` |
| `triggered_by` | string? | GitHub login that triggered the job |
| `env` | object? | Public environment variables (secrets removed) |
| `user_env` | object? | User-supplied environment variables |
| `artifacts` | string[]? | Existing artifact paths |

### Example

```json
{
  "uid": "e3b0c44298fc1c149afbf4c8996fb924",
  "commit": {
    "sha": "0123456789abcdef0123456789abcdef01234567",
    "tree": "abcdef0123456789abcdef0123456789abcdef01",
    "message": "tests/sys/shell: fix thing\n\nDetails...",
    "author": "contributor"
  },
  "ref": "refs/heads/master",
  "creation_time": 1760000000.0,
  "start_time": 1760000003.0,
  "fasttracked": false,
  "status": {"status": "finished", "total": 123, "passed": 123, "failed": 0},
  "state": "passed",
  "output": "...",
  "output_text_url": "https://ci.example.org/results/e3b0.../output.txt",
  "runtime": 123.4,
  "trigger": "push",
  "triggered_by": "contributor",
  "env": {
    "CI_JOB_UID": "e3b0...",
    "CI_BUILD_COMMIT": "0123...",
    "CI_BUILD_REF": "refs/heads/master",
    "CI_BUILD_BRANCH": "master"
  },
  "artifacts": ["output.txt"]
}
```

## `CommitModel`

| Field | Type | Description |
| --- | --- | --- |
| `sha` | string | Commit SHA |
| `tree` | string | Tree SHA |
| `message` | string | Full commit message |
| `author` | string | GitHub login, or git author name if the commit has no GitHub user |

## `PullRequestInfo`

| Field | Type | Description |
| --- | --- | --- |
| `title` | string | PR title |
| `number` | integer | PR number |
| `merge_commit` | string | GitHub's merge commit SHA |
| `user` | string | PR author login |
| `url` | string | HTML URL |
| `base_repo` | string | Base repository clone URL |
| `base_branch` | string | Target branch name |
| `base_commit` | string | Target branch head SHA |
| `base_full_name` | string | Target repository full name |
| `mergeable` | boolean | Mergeable flag |
| `labels` | string[] | Sorted label names |
| `state` | string | `open` / `closed` |
| `is_merged` | boolean | Whether the PR was merged |

## Manual-job parameters

### `ManualJobBranchParamModel`

| Field | Type | Required | Default |
| --- | --- | --- | --- |
| `branch` | string | yes | None |
| `env` | object | no | `null` |
| `fasttrack` | boolean | no | `false` |

### `ManualJobTagParamModel`

Same as branch, with `tag` instead of `branch`.

### `ManualJobCommitParamModel`

Same as branch, with `sha` instead of `branch`.

## `JobQueryModel`

Query parameters for `GET /jobs`. See
[Jobs API](/api/jobs/#query-parameters) for the full table.

| Field | Type | Default |
| --- | --- | --- |
| `limit` | integer | 25 |
| `uid` | string | `null` |
| `is_pr` | boolean | `null` |
| `is_branch` | boolean | `null` |
| `is_tag` | boolean | `null` |
| `states` | string | `null` |
| `prnum` | integer | `null` |
| `prstates` | string | `null` |
| `branch` | string | `null` |
| `tag` | string | `null` |
| `ref` | string | `null` |
| `sha` | string | `null` |
| `tree` | string | `null` |
| `author` | string | `null` |
| `after` | date string | `null` |
| `before` | date string | `null` |

## Status payload

The `PUT /job/{uid}/status` body is intentionally untyped. The server only
requires:

```json
{"status": {"status": "working"}}
```

Scripts commonly send:

| Field | Type | Meaning |
| --- | --- | --- |
| `status` | string | Free-form phase (`fetching code`, `working`, `finished`, ...) |
| `total` | integer | Total jobs |
| `passed` | integer | Passed jobs |
| `failed` | integer | Failed jobs |
| `eta` | string | Estimated time remaining |
| `failed_jobs` | array | `{name, href?}` |
| `failed_builds` | array | `{application, target, toolchain, worker, runtime}` |
| `failed_tests` | array | `{application, target, toolchain, worker, runtime}` |

When a job finishes, Murdock changes `status.status` from `working` to
`finished` before storing it.

## States and statuses

- Job states: `queued`, `running`, `passed`, `errored`, `stopped`.
- PR states (from GitHub): `open`, `closed`.
- Commit statuses (sent to GitHub): `pending`, `success`, `failure`.
- Task results: `passed`, `failed` (metrics) / `passed`, `errored`,
  `stopped` (job state).
