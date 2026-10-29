---
title: Notifications
description: Mail and Matrix notifications, routing by trigger type, and duplicate suppression.
---

Murdock can notify on finished jobs through two notifiers: email and
Matrix. Notifications are disabled by default.

```dotenv
MURDOCK_NOTIFIER_ENABLE=1
```

## Routing

The notifier used depends on the job source:

| Trigger | Setting | Default |
| --- | --- | --- |
| Pull request | `MURDOCK_NOTIFIER_PR_NOTIFIERS` | `["matrix"]` |
| Branch push | `MURDOCK_NOTIFIER_BRANCH_NOTIFIERS` | `["mail", "matrix"]` |
| Tag push | `MURDOCK_NOTIFIER_TAG_NOTIFIERS` | `["mail", "matrix"]` |
| Other commits | `MURDOCK_NOTIFIER_COMMIT_NOTIFIERS` | `["matrix"]` |

Only `passed` and `errored` jobs produce notifications. Stopped jobs do not.

For branch and tag jobs, Murdock checks the most recent previous job for the same
ref. If both the previous and the new job passed, the notification is skipped, so
a long-running branch does not produce a message for every successful build.

## Mail

```dotenv
MURDOCK_NOTIFIER_MAIL_RECIPIENTS=ci@example.org,maintainer@example.org
MURDOCK_NOTIFIER_MAIL_SERVER=smtp.example.org
MURDOCK_NOTIFIER_MAIL_PORT=587
MURDOCK_NOTIFIER_MAIL_USE_TLS=1
MURDOCK_NOTIFIER_MAIL_USERNAME=ci
MURDOCK_NOTIFIER_MAIL_PASSWORD=secret
```

The message subject is `Murdock job <state> - <title>` and the body contains a
link to the job details page. SMTP authentication/connection failures are logged
and ignored. They do not fail the job.

## Matrix

```dotenv
MURDOCK_NOTIFIER_MATRIX_ROOM=!roomid:matrix.org
MURDOCK_NOTIFIER_MATRIX_TOKEN=syt_...
```

Murdock posts an HTML-formatted `m.room.message` to
`https://matrix.org/_matrix/client/v3/rooms/<room>/send/m.room.message`. For PR
jobs it tries to resolve the PR author's display name to a Matrix member ID and
mentions them. If that lookup fails, it falls back to `@<github-user>`.

Matrix read timeouts and HTTP errors are logged and ignored.

## What is not configurable

- The notifier implementation is selected by name (`mail`, `matrix`). There is
  no plugin registry beyond those two.
- Notifications are sent before the job is inserted into the database, because
  the branch/tag duplicate check queries the previous job.
- The mail sender is hard-coded to `ci@riot-os.org` in the notifier.
