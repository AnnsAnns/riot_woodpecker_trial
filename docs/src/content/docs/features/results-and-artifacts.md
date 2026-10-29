---
title: Results and artifacts
description: Work directories, output.txt, the /results route, and RIOT result files.
---

Murdock stores everything a job produces in a per-job work directory and serves
it as static files. There is no object store or artifact upload step.

## Work directory

```text
$MURDOCK_WORK_DIR/
└── <job uid>/
    ├── output.txt
    ├── <artifact files or directories>
    └── ... anything the task wrote
```

The directory is created when the job starts. It is removed when a finished job
is deleted, or when a stopped job is not kept (`MURDOCK_STORE_STOPPED_JOBS=0`).

`MURDOCK_WORK_DIR` is mounted at `/results`:

```python
app.mount("/results", StaticFiles(directory=GLOBAL_CONFIG.work_dir, html=True, check_dir=False))
```

The `html=True` option means a directory with `index.html` is rendered directly,
which is why artifact directories such as `doc-preview/` work in a browser.

## Output

Murdock writes the merged stdout/stderr to `output.txt` and exposes its URL in
the job model as `output_text_url`:

```text
<MURDOCK_BASE_URL>/results/<uid>/output.txt
```

The in-memory `output` field also contains the full text. The web UI streams new
lines over the WebSocket while the job is running and falls back to
`output_text_url` for finished jobs.

## Artifacts

Artifacts are declared in `.murdock.yml`:

```yaml
artifacts:
  - output.txt
  - doc-preview/
  - result.json
```

After all tasks, Murdock checks each path relative to the work directory and
stores the ones that exist in the job's `artifacts` list. The `/results` route
then serves them under:

```text
<MURDOCK_BASE_URL>/results/<uid>/<artifact>
```

PR comments can link selected artifacts through `pr.comment_artifacts`.

## RIOT result files

RIOT's `murdock-scripts/process_result.py` converts the raw `result.json` into
files that the Murdock UI understands:

| File | Contents |
| --- | --- |
| `result.json` | Raw per-job results collected from the build worker. `build.sh` compresses it to `result.json.gz` after processing. |
| `builds.json` | Per-application build counts and successes/failures |
| `build_failures.json` | Flattened build failure list |
| `tests.json` | Per-application test counts and successes/failures |
| `test_failures.json` | Flattened test failure list |
| `stats.json` | Job counts, total time, per-worker statistics |
| `output/builds/<app>/<target>:<toolchain>.txt` | Build log for one target |
| `output/builds/<app>/app.json` | Per-application build result data |
| `output/tests/<app>/<target>:<toolchain>.txt` | Test log for one target |
| `output/tests/<app>/app.json` | Per-application test result data |
| `doc-preview/` | Generated Doxygen documentation |

The UI (`murfrog`) reads `builds.json`, `tests.json`, `stats.json`, and the
per-application `app.json` files through `/results/<uid>/...`.

See [RIOT job aggregation](/features/riot-job-aggregation/) for how RIOT
produces these files from many build and test subjobs.

## Retention

Finished jobs and their directories persist until:

- `DELETE /job/{uid}` removes one job,
- `DELETE /jobs?before=YYYY-MM-DD` removes jobs older than a date,
- the work directory is removed manually.

There is no automatic retention policy in the server. Plan disk usage and
cleanup for long-running instances.
