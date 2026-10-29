---
title: RIOT CI
description: How RIOT's .murdock script discovers jobs, selects boards, gates builds, and caches results.
---

RIOT's CI logic lives in the RIOT repository, not in the Murdock server. The
server schedules a job and runs a script. RIOT's `.murdock` script is that
script's main entry point for build and test discovery. This page documents the
RIOT-specific layer so the server documentation can be read in context. See
[RIOT job aggregation](/features/riot-job-aggregation/) for how RIOT collects
many build and test subjobs into one Murdock job.

:::note
The exact script invocation depends on the deployment generation. The legacy
`murdock-scripts/build.sh` uses `dwq` to fan jobs out to workers. A modern
deployment can use a wrapper script or job image that calls the same `.murdock`
commands. The job-generation logic below is the same either way.
:::

## `get_jobs`

The core interface is:

```sh
./.murdock get_jobs
```

It prints a list of commands, one per job:

```text
./.murdock static_tests
./.murdock compile examples/basic/hello-world samr21-xpro:gnu
```

A compile job can spawn a `run_test` job for native or emulated boards. The
legacy `test_job` helper can also emit `./.murdock run_test <app> <board>:<toolchain>`.

Murdock (or the old `build.sh`) consumes that list and executes or queues the
commands. Each command prints its own output and exits with a status code.

## Compile jobs

`get_compile_jobs`:

1. Returns immediately if the `CI: skip compile test` label is set.
2. Calls `update_changed_modules` to apply `can_fast_ci_run.py` change
   detection.
3. Enumerates applications with `make info-applications`, filtered by `APPS`.
4. For each application, enumerates supported boards and toolchains with
   `make info-boards-supported` / `info-toolchains-supported`.
5. Emits one `./.murdock compile <app> <board>:<toolchain>` per pair.

The board filter comes from:

- `BOARDS` if set,
- `BOARDS_CHANGED` if change detection identified affected boards,
- the quickbuild board list for quick builds,
- all supported boards for full builds.

### Quickbuild boards

Quick builds compile a representative subset of boards:

```text
adafruit-itsybitsy-m4
atmega256rfr2-xpro
esp32-wroom-32
esp32s3-devkit
frdm-k64f
hifive1b
msb-430
msba2
native32
native64
nrf52840dk
qn9080dk
samr21-xpro
stk3200
stm32f429i-disc1
```

Changed boards are added to this list when the change detector identifies them.

### Toolchains

Most boards are built with GNU. A subset is also built with LLVM to keep
regression coverage without doubling all builds:

```text
iotlab-m3 native32 native64 nrf52dk mulle nucleo-f401re samr21-xpro slstk3402a
```

This list is `TEST_BOARDS_LLVM_COMPILE`.

### `can_fast_ci_run.py`

`dist/tools/ci/can_fast_ci_run.py` inspects the diff between the commit and its
base and can restrict the build to changed applications and boards:

- changed app → build that app on all selected boards,
- changed board → build all applications on that board,
- changed modules/build system → request a full build,
- no relevant changes → skip compile jobs entirely.

It is skipped when:

- there is no base commit,
- `FULL_BUILD=1`,
- `BOARDS` or `APPS` is set explicitly,
- the `CI: full build` label is present.

The static-tests job prints the `can_fast_ci_run.py` explanation. It also
prints `MURDOCK_TEST_CHANGE_FILTER` when that variable is set.

## Full builds, merge queues, and nightly

`FULL_BUILD=1` when:

- `NIGHTLY=1`, or
- the `CI: full build` label is set.

`QUICK_BUILD=0` (full board set) when:

- the branch starts with `gh-readonly-queue/`,
- `FULL_BUILD=1`,
- otherwise `QUICK_BUILD=1`.

A merge-queue branch uses the full board set. If no base commit is available,
change detection is skipped and RIOT builds all applications. `build.sh` can
provide a merge base, so change detection can still narrow the application
list.

## Build and test execution

### `compile`

```sh
BOARD=<board> TOOLCHAIN=<toolchain> RIOT_CI_BUILD=1 \
  make -C<app> all test-input-hash -j<JOBS>
```

After a successful build:

- native and emulated boards run tests inline on the same worker,
- hardware boards run `make test-murdock` on the same worker when
  `TEST_BOARDS_AVAILABLE` contains the board,
- a test cache hit skips the hardware test,
- the build directory is removed and its size is logged.

### `run_test`

`run_test` is used by the inline `dwq-localjob` path for native and emulated
boards. The legacy `test_job` helper can also queue it on a board queue.

`run_test` expects the compiled binary in `$(pwd)/build`. The compile job
normally creates it. A separate test job must build the application first.

```sh
BOARD=<board> TOOLCHAIN=<toolchain> make -C<app> flash-only termdeps -j2
BOARD=<board> TOOLCHAIN=<toolchain> make -C<app> test
```

Some applications use `test-with-config` instead:

```text
examples/advanced/suit_update
tests/drivers/at86rf2xx_aes
```

A successful test stores its test hash in Redis.

### `static_tests`

Runs the RIOT static-test suite if `STATIC_TESTS=1` and always prints the
`can_fast_ci_run.py` explanation.

## Labels

| Label | Effect |
| --- | --- |
| `CI: ready for build` | Required for PR jobs (server gate) |
| `CI: full build` | Force `FULL_BUILD=1` |
| `CI: skip compile test` | Skip all compile jobs. This label also marks the job fasttracked by default |
| `CI: run tests` | Enable hardware tests (`RUN_TESTS=1`) |
| `CI: no fast fail` | Legacy build script sets `DWQ_MAXFAIL=500` instead of `0` |
| `CI: disable test cache` | Bypass the test-result cache |
| `Process: release backport` | Fasttracked by default |

## Caching

RIOT's CI uses four shared caches:

- ccache: remote Redis cache. Job containers use `CCACHE_REMOTE_ONLY=1`
  and `CCACHE_REMOTE_STORAGE=redis://...`.
- test-result cache: Redis keyed by the test input hash. A hit skips the
  hardware test.
- git-cache: shared object store using git alternates. Per-job checkouts
  do not transfer objects repeatedly.
- download cache: `DLCACHE_DIR` for package tarballs.

The legacy worker fleet shares these through a Redis instance and an SSH bridge. The modern server expects the job environment to provide access to them.

## Hardware-in-the-loop

Boards available for physical testing are configured by
`TEST_BOARDS_AVAILABLE` (empty by default in the RIOT script). The current
script runs `make test-murdock` on the compile worker when the board is in that
list. The `test_job` helper can instead queue `run_test` on a board queue, but
the current `.murdock` script does not call it. Emulated boards are listed in
`EMULATED_BOARDS_AVAILABLE`. The script includes a commented `microbit` example.

Without board agents, `test_job` jobs remain queued because no worker listens
on the board queue.

## Result processing

`murdock-scripts/process_result.py` turns the raw job results into the files the
UI reads (`builds.json`, `tests.json`, `stats.json`, per-application `app.json`,
and per-target output). `reporter.py` streams live progress to the Murdock API
through `PUT /job/<uid>/status`, including failed build/test lists.

See [Results and artifacts](/features/results-and-artifacts/) for the file
layout and [Tasks and execution](/features/tasks-and-execution/) for how the
server runs the script.
