---
title: .murdock.yml reference
description: Complete schema, defaults, and examples for Murdock's per-repository configuration.
---

`.murdock.yml` is fetched from the commit being built. Missing or invalid files
fall back to the defaults below. All fields are optional unless noted.

## Schema

```yaml
push:
  branches: []        # list[str]
  tags: []            # list[str]

pr:
  enable_comments: false
  sticky_comment: false
  comment_artifacts:  # list[{name: str, readable_name?: str}]
    []
  comment_footer: null

commit:
  skip_keywords: []   # list[str]

env: {}               # dict[str, str]

failfast: false

artifacts: []         # list[str], paths relative to the job work dir

tasks:                # list[TaskSettings]
  - name: null        # optional display name
    image: null       # Docker image; defaults to MURDOCK_DOCKER_DEFAULT_TASK_IMAGE
    command: null     # command passed to the image
    env: {}           # extra env for this task
```

If `tasks` is absent, Murdock uses a single default task and runs
`MURDOCK_SCRIPT_NAME` in script mode.

## Field reference

### `push.branches`

List of accepted push branches. Matching uses `*`, exact equality, or
`re.match`. Empty list = no branches accepted.

### `push.tags`

Same for tags. Branch and tag rules are independent.

### `pr.enable_comments`

Post a result comment after a PR job finishes. Also requires
`MURDOCK_ENABLE_PR_COMMENT`.

### `pr.sticky_comment`

Update an existing comment whose first line is `### Murdock results` instead of
creating a new one.

### `pr.comment_artifacts`

Artifacts to link in the PR comment. `readable_name` replaces the raw path in
the link text.

```yaml
pr:
  comment_artifacts:
    - name: doc-preview/
      readable_name: Documentation preview
```

### `pr.comment_footer`

Text appended after the generated result table and artifact links.

### `commit.skip_keywords`

If any keyword is a substring of the commit message, the job is skipped and a
pending commit status is set.

### `env`

String-to-string environment variables. Merged below manual-job and task-level
variables.

### `failfast`

Stop the job when a status update reports `failed_jobs`, `failed_builds`, or
`failed_tests`.

### `artifacts`

Paths relative to the work directory. Existing paths are added to the job's
`artifacts` list. Directories must contain `index.html` if the UI is expected
to render them.

### `tasks`

Ordered list of tasks. Fields:

| Key | Type | Default |
| --- | --- | --- |
| `name` | string | `null` |
| `image` | string | `MURDOCK_DOCKER_DEFAULT_TASK_IMAGE` |
| `command` | string | `null` |
| `env` | object | `{}` |

Tasks run sequentially. Execution stops after a task returns `stopped` or
`errored`.

## RIOT example

```yaml
push:
  branches:
    - '^staging$'
    - '^trying$'
    - '^gh-readonly-queue/'

pr:
  enable_comments: true
  sticky_comment: true
  comment_artifacts:
    - name: doc-preview/
      readable_name: Documentation preview

commit:
  skip_keywords: ["ci_skip", "murdock_skip", "[ci skip]"]

artifacts:
  - output.txt
  - doc-preview/
```

RIOT's `.murdock` script consumes additional environment variables and labels. The RIOT CI page documents them in [RIOT CI](/features/riot-ci/).
