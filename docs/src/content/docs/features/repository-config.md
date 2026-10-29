---
title: Repository configuration
description: Per-repository .murdock.yml configuration, defaults, and behavior.
---

Murdock reads `.murdock.yml` from the exact commit being built through the
GitHub contents API. Each job therefore uses the configuration that belongs to
its commit, not the latest default branch.

If the file is missing, empty, invalid YAML, or fails validation, Murdock logs a
warning and falls back to `MurdockSettings()` default values. There is no
repository-level error state.

## Full example

```yaml
push:
  branches:
    - '^staging$'
    - '^trying$'
    - '^gh-readonly-queue/'
  tags:
    - '^v[0-9]+\.[0-9]+$'

pr:
  enable_comments: true
  sticky_comment: true
  comment_artifacts:
    - name: doc-preview/
      readable_name: Documentation preview
  comment_footer: |
    Powered by Murdock.

commit:
  skip_keywords:
    - ci_skip
    - murdock_skip
    - '[ci skip]'

env:
  RIOT_CI_BUILD: '1'

failfast: true

artifacts:
  - output.txt
  - doc-preview/

tasks:
  - name: build
    image: riot/riotbuild:latest
    command: ./build.sh
    env:
      BOARD: native64
  - name: report
    command: ./report.sh
```

## `push`

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `branches` | list of strings | `[]` | Branch names accepted for push events |
| `tags` | list of strings | `[]` | Tag names accepted for push events |

Each entry is matched with `*`, exact equality, or a Python regular expression.
An empty list accepts nothing.

## `pr`

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `enable_comments` | bool | `false` | Post a result comment on PRs after the job finishes |
| `sticky_comment` | bool | `false` | Update one existing “Murdock results” comment instead of posting a new one |
| `comment_artifacts` | list | `[]` | Artifacts to link in the PR comment (`name`, optional `readable_name`) |
| `comment_footer` | string | `null` | Text appended to the PR comment |

PR comments are also gated globally by `MURDOCK_ENABLE_PR_COMMENT`.

## `commit`

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `skip_keywords` | list of strings | `[]` | If any keyword occurs in the commit message, skip the job |

## `env`

A string-to-string map merged into the job environment. Precedence, from lowest
to highest:

1. Murdock's built-in `CI_*` variables,
2. `MURDOCK_CUSTOM_ENV`,
3. `.murdock.yml` → `env`,
4. manual-job `env` / `user_env`,
5. task-level `env` (only for that task).

## `failfast`

When `true`, Murdock stops the job as soon as a status update reports failed
jobs, builds, or tests. See [Jobs and scheduling](/features/jobs/#failfast).

## `artifacts`

A list of paths relative to the job work directory. After all tasks finish,
Murdock checks which paths exist and exposes the existing ones in the job's
`artifacts` field. Directories are allowed. The web UI expects a directory to
contain an `index.html` if it is rendered inline.

## `tasks`

A job runs the tasks in order. Each task supports:

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `name` | string | `null` | Display name used in the output and logs |
| `image` | string | `MURDOCK_DOCKER_DEFAULT_TASK_IMAGE` | Docker image (Docker mode only) |
| `command` | string | `null` | Command to run (Docker mode) or override (script mode ignores it) |
| `env` | map | `{}` | Extra environment variables for this task |

If `tasks` is omitted, Murdock creates one default `TaskSettings()` and runs the
configured script (`MURDOCK_SCRIPT_NAME`, default `run.sh`) in script mode. See
[Tasks and execution](/features/tasks-and-execution/).

:::note
GNU Make and the RIOT build system expect an `env` value to be a string. YAML
numbers or booleans are converted to strings by the environment construction,
but quoting values such as `RIOT_CI_BUILD: '1'` is safer.
:::
