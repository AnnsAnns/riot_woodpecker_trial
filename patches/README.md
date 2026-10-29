# Submodule patches

This directory contains patches for the git submodules. Apply them without
editing the submodule source in place.

The patches apply to the `murdock` submodule at commit
`8f38a433df4d89f2292e3db139adf0db9d811db5`. Rebase them if the submodule moves.

## Patches

| Patch | Change |
| --- | --- |
| `murdock/0001-fix-running-runtime.patch` | Return the live elapsed time for a running job instead of a negative value |
| `murdock/0002-fix-ref-deletion-order.patch` | Cancel queued jobs and stop running jobs in the correct order when a ref is deleted |
| `murdock/0003-fix-openapi-summaries.patch` | Correct two OpenAPI summaries for the job deletion and manual commit endpoints |
| `murdock/0004-fix-model-titles.patch` | Correct spelling in the job model field titles |

The local RIOT demo does not need these patches. They fix behavior and text
issues found during the guide review.

## Apply

From the repository root:

```sh
./patches/apply.sh check    # check that all patches apply
./patches/apply.sh apply    # apply all patches
./patches/apply.sh revert   # reverse all patches
```

The script uses `git -C murdock apply`. It does not commit or push.

## Add a patch

Make the change in a temporary copy, then write a unified diff with paths
relative to the submodule root:

```text
--- a/murdock/job.py
+++ b/murdock/job.py
```

Save it under `patches/<submodule>/` with a numbered name. The apply script
reads every `.patch` file for the selected submodule.
