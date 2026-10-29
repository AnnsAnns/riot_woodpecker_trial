---
title: Job environment
description: Environment variables Murdock exposes to every job, and the precedence rules.
---

Every task receives a copy of the job environment plus its own task-level `env`.
The variables are built in `MurdockJob.env` and `Task`.

## Always present

| Variable | Value |
| --- | --- |
| `CI_SCRIPTS_DIR` | `MURDOCK_SCRIPTS_DIR` (removed from API responses) |
| `CI_MURDOCK_PROJECT` | `MURDOCK_PROJECT` |
| `CI_BASE_URL` | `MURDOCK_BASE_URL` |
| `CI_JOB_UID` | Job UID (UUID hex) |
| `CI_JOB_TOKEN` | Random job token (removed from API responses) |
| `CI_BUILD_TREE` | Commit tree SHA |

## Pull-request jobs

| Variable | Value |
| --- | --- |
| `CI_PULL_COMMIT` | PR head SHA |
| `CI_PULL_REPO` | `GITHUB_REPO` |
| `CI_PULL_NR` | PR number |
| `CI_PULL_URL` | PR HTML URL |
| `CI_PULL_USER` | PR author login |
| `CI_BASE_REPO` | Base repository clone URL |
| `CI_BASE_BRANCH` | Target branch name |
| `CI_BASE_COMMIT` | Target branch head SHA |
| `CI_PULL_LABELS` | Semicolon-separated labels |
| `CI_MERGE_COMMIT` | GitHub merge commit SHA (only if mergeable and available) |

## Branch, tag, and commit jobs

Present when `ref` is set:

| Variable | Value |
| --- | --- |
| `CI_BUILD_COMMIT` | Commit SHA |
| `CI_BUILD_REF` | Full ref |
| `CI_BUILD_REPO` | `GITHUB_REPO` |
| `CI_BUILD_BRANCH` | Branch name, for `refs/heads/...` |
| `CI_BUILD_TAG` | Tag name, for `refs/tags/...` |

Manual commit jobs use the literal ref `Commit <sha>`, so they set
`CI_BUILD_COMMIT` and `CI_BUILD_REF` but not `CI_BUILD_BRANCH`/`CI_BUILD_TAG`.

## Precedence

From lowest to highest:

1. Murdock's built-in variables above,
2. `MURDOCK_CUSTOM_ENV`,
3. `.murdock.yml` → `env`,
4. manual-job `env` (stored as `user_env`),
5. task `env` (only for that task).

## Secrets

`CI_JOB_TOKEN` and `CI_SCRIPTS_DIR` are removed from the public `env` field in
API responses. All other variables, including `.murdock.yml` values and
`user_env`, are visible through the API. Do not put secrets in `.murdock.yml` or
manual-job `env`.

## RIOT variables

RIOT's `.murdock` script reads additional variables that can be provided by the
job script or the deployment:

| Variable | Meaning |
| --- | --- |
| `CI_BUILD_BRANCH`, `CI_BASE_BRANCH`, `CI_BASE_COMMIT` | Branch/merge-base detection |
| `CI_PULL_LABELS` | Label gates |
| `BOARDS`, `APPS` | Explicit build filters |
| `APPS_CHANGED`, `BOARDS_CHANGED` | `can_fast_ci_run.py` output |
| `FULL_BUILD`, `QUICK_BUILD` | Build scope |
| `NIGHTLY` | Nightly mode |
| `RUN_TESTS` | Enable hardware tests |
| `STATIC_TESTS` | Run static tests |
| `ENABLE_TEST_CACHE` | Use the Redis test cache |
| `TEST_HASH` | Test cache key |
| `MURDOCK_REDIS_HOST` | Redis host for test cache |
| `DLCACHE_DIR` | Package download cache |
| `MURDOCK_HOOK` | Optional hook script |
| `MURDOCK_TEST_CHANGE_FILTER` | Print change-filter diagnostics |
