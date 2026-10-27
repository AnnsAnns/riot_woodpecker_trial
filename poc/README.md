# RIOT CI on Woodpecker — Murdock-compatible proof of concept

This directory contains a proof of concept for running **RIOT OS's Murdock CI
behaviour on [Woodpecker CI](https://woodpecker-ci.org)**, locally, on a single
node. It aims to reproduce Murdock's job discovery as closely as possible — not
a toy subset.

## Architecture

Woodpecker cannot enumerate Murdock's unbounded job set itself: a configuration
extension has a **10 s timeout** and pipeline config is taken from the repo.
So, exactly like Murdock's `murdock-scripts/build.sh`, the job set is discovered
**at runtime in a job** and then dispatched:

```
 push / PR / merge-queue
        │  webhook
        ▼
 Woodpecker server ── config extension ──▶ bootstrap workflow
        │                                      │ runs dispatch.py:
        │                                      │  1. real `.murdock get_jobs`
        │                                      │     (stubbed dwqc captures jobs)
        │                                      │  2. one pipeline per Murdock job,
        │                                      │     carrying the whole job list
        ▼                                      ▼
   job workflows  ◀── config extension ◀── Woodpecker API (MURDOCK_BATCH)
   (riot/riotbuild)   expands the batch      │  real
                      into 1 workflow/job     └▶ `.murdock compile` / `run_test` / `static_tests`
```

The dispatcher starts **one Woodpecker pipeline per Murdock job**, and the
extension expands the job list (`MURDOCK_BATCH`) into **one workflow per
build/test**. So the Woodpecker pipeline page lists the same builds/tests that
murfrog lists for a Murdock job — grouped under one pipeline with one overall
status, instead of thousands of unrelated pipelines.

Concept mapping:

| Murdock | Woodpecker (this PoC) |
| --- | --- |
| `murdock-scripts/build.sh` | `config-extension/dispatch.py` (bootstrap step) |
| build.sh PR merge commit → `cache_repo` | dispatcher merges head into base, pushes `refs/heads/murdock/build/<sha>`, jobs build it |
| `.murdock get_jobs` | **the real `.murdock get_jobs`**, run with a stubbed `dwqc` |
| `dwqc` / disque dispatch | one Woodpecker pipeline per Murdock job, expanded into one workflow per build/test |
| `dwqw` worker fleet | Woodpecker agents |
| per-board test queues | workflow `labels` (agent selection) |
| `riot/murdock-worker` | step `image:` (`riot/riotbuild:latest`) |
| `.murdock compile` / `run_test` | the **real** commands, run by the job workflow |
| `murfrog` UI | Woodpecker UI |
| GitHub webhooks | Forgejo webhooks |

Because the dispatcher runs the **actual `.murdock`**, the job set matches
Murdock exactly, including all the subtle behaviour: quickbuild vs full build,
merge-queue (`gh-readonly-queue/`) full builds, `can_fast_ci_run` change
detection, `CI: full build` / `CI: skip compile test` / `CI: run tests` /
`CI: no fast fail` labels, all supported boards and toolchains, native/emulated
tests inline, and static tests.

## Layout

```
poc/
├── docker-compose.poc.yml      # Forgejo + Woodpecker server/agent + extension
├── config-extension/
│   ├── server.py               # the config extension (bootstrap / job / gated)
│   ├── dispatch.py             # build.sh + .murdock get_jobs analogue (dispatcher)
│   └── sample-request.json
├── pipelines/
│   └── riot-build.yaml         # Phase 1: static baseline pipeline
├── scripts/
│   ├── poc-up.sh               # bring up the stack + activate repo + secret
│   ├── poc-trigger-pr.sh       # create/label a PR and push -> quickbuild
│   ├── poc-trigger-mergequeue.sh # push gh-readonly-queue/... -> full build
│   ├── poc-trigger.sh          # push to a branch
│   ├── compare-jobs.py         # diff Murdock's job set vs a dispatched pipeline
│   ├── poc-down.sh             # tear down (-v wipes data)
│   └── forgejo_login.py        # headless Forgejo OAuth login -> API token
└── README.md
```

## Prerequisites

- Docker + Docker Compose, `woodpecker-cli` v3.19.x on `PATH`
- a local RIOT checkout (defaults to `../RIOT`)
- two images:
  ```sh
  docker build -t riotbuild-lite:poc poc/riotbuild-lite   # small: git/gcc/python3/make
  docker pull riot/riotbuild:latest                       # ~13 GB: full toolchains
  ```

`riotbuild-lite` is only used for the bootstrap discovery step (it needs git,
make and python3, not the cross toolchains). The actual compile/test jobs use
the real `riot/riotbuild`. Set `POC_BOOTSTRAP_IMAGE` / `POC_JOB_IMAGE` to
override.

### Networking

Every service runs with `network_mode: host` and all generated steps carry
`network_mode: host`, so **nothing resolves a container name** — containers,
step containers and host-side tools all use `127.0.0.1`:

| service | address |
| --- | --- |
| Forgejo HTTP | `http://localhost:3000` |
| Forgejo SSH | `localhost:2222` |
| Woodpecker HTTP/UI | `http://localhost:8000` |
| Woodpecker gRPC | `localhost:9000` |
| config extension | `http://localhost:8001/config` |
| redis (ccache + test cache) | `localhost:6379` |

Those host ports must be free. Two consequences:

- the repo must be **network trusted** (`poc-up.sh` sets
  `wp repo update --trusted-network`), because Woodpecker only accepts
  `network_mode` from trusted repositories;
- `WOODPECKER_BACKEND_DOCKER_NETWORK` is deliberately *not* set. The docker
  backend implements it as `docker network connect <name>`, which cannot work
  for `host` (the network is entered at container create time, via the step's
  `network_mode`).


## Running

```sh
./scripts/poc-up.sh           # Forgejo + Woodpecker + extension; RIOT pushed; repo activated
./scripts/poc-trigger-pr.sh   # PR with 'CI: ready for build' -> quickbuild
#   or
./scripts/poc-trigger.sh      # push to the current branch (gated unless it matches push.branches)
./scripts/poc-down.sh -v      # tear down
```

Then watch pipelines:

```sh
woodpecker-cli --server http://localhost:8000 --token "$(cat poc/.token)" pipeline ls pocadmin/RIOT
```

## Observed result

A labelled PR touching `tests/sys/shell` produces **one pipeline per Murdock
job**, on the default branch, whose **workflows are the builds/tests**:

```
pipeline #4  "PR #1 (abbfa1b)"   branch master   76 workflows
  success  static tests
  success  tests_sys_shell adafruit-itsybitsy-m4:gnu
  success  tests_sys_shell atmega256rfr2-xpro:gnu
  success  tests_sys_shell esp32-wroom-32:gnu
  success  tests_sys_shell frdm-k64f:gnu        # ARM
  success  tests_sys_shell hifive1b:gnu         # RISC-V
  success  tests_sys_shell msba2:gnu            # ARM7
  failure  tests_sys_shell native32:llvm        # clang -Werror (real result)
  failure  tests_sys_shell native64:llvm
  running  tests_sys_shell ...
  pending  tests_sys_shell ...
```

Open it at http://localhost:8000/repos/1/pipeline/4 — that's the murfrog-like
view: one job, every build/test, pass/fail, with logs per workflow.

(The two `llvm` failures are real: the demo commit adds an unused `static
variable`, which clang rejects under `-Werror`; GCC accepts it.)

Job count: the real `.murdock get_jobs` expands the changed-app regex across the
quickbuild board list, giving 75 compile jobs + 1 static here. A merge-queue
(`gh-readonly-queue/`) branch instead produces a **full build** (all supported
boards for each app).

`POC_BATCH_SIZE` controls how many jobs go into one pipeline (default: all in
one, so the UI shows a single grouped job). Set it lower to split very large
runs across several pipelines.

## Caching

Murdock's shared caches are reproduced:

- **ccache** — a `redis-ccache` service on the `poc` network; job containers run
  with `CCACHE=ccache`, `CCACHE_REMOTE_ONLY=1` and
  `CCACHE_REMOTE_STORAGE=redis://redis-ccache:6379` (Murdock's
  `redis+unix` backend, over TCP). The first build populates redis; later
  builds hit it (a repeat build added ~32 keys vs ~1670 the first time).
- **test-result cache** — same redis, addressed via `MURDOCK_REDIS_HOST`; the
  job image ships `redis-cli` so `.murdock`'s `test_cache_get/put` work.
- **git object cache (`git-cache`)** — job workflows set `skip_clone: true` and
  the step runs `git-cache clone "$CI_REPO_CLONE_URL" . --commit "$MURDOCK_COMMIT"`.
  Objects are shared from `$GIT_CACHE_DIR` (`/cache/.gitcache`) via git
  alternates: the first checkout on a worker populates the cache (~8 s), every
  later one is ~1 s with no object transfer over the network. This is what makes
  thousands of per-job checkouts cheap (Murdock's `git-cache`).
- **download cache** — shared `poc-cache` volume at `/cache` (`DLCACHE_DIR`).

The job image is `riotbuild-cached:poc` (`riot/riotbuild` + `redis-tools`):

```sh
docker build -t riotbuild-cached:poc poc/riotbuild-cached
```

## Fidelity: comparing against Murdock

`scripts/compare-jobs.py <pipeline>` reads a dispatched pipeline's
`MURDOCK_BATCH` (what Woodpecker runs) and diffs it against a fresh, real
`.murdock get_jobs` on the same ref (what Murdock runs):

```
$ python3 scripts/compare-jobs.py 12
pipeline 12: 'MANUAL: PR #1 (ee2fa8e) @ master' ref=refs/heads/murdock/build/ee2fa8e8...
woodpecker jobs: 19   murdock jobs: 19
IDENTICAL ✓
```

For PRs the dispatcher reproduces `build.sh` exactly: it merges the PR head
into the **current** base branch head, pushes the merge, and the jobs build the
merge commit (Murdock's `CI_MERGE_COMMIT`).

### Why a run only tests a few apps

`.murdock`'s changed-app filter is a **regex** (`.murdock: get_apps | grep -E
"$APPS"`). A PR that only touches `tests/sys/shell/main.c` selects
`tests/sys/shell` and therefore also matches its siblings:

```
tests/sys/shell  tests/sys/shell_ble  tests/sys/shell_coreclk
tests/sys/shell_lock  tests/sys/shell_scripting
```

so the quickbuild covers those 5 apps across the quickbuild boards. Change a
different app and only that app is built; change a module/`makefiles/` and
`can_fast_ci_run` requests a **full build** (all apps); a `gh-readonly-queue/`
branch forces a full build. Use `POC_PR_APP=<app> ./scripts/poc-trigger-pr.sh`
to try another app.

### Merge queue = the entire test suite

A push to a `gh-readonly-queue/<base>/…` branch (also `CI: full build` /
nightly) sets `QUICK_BUILD=0`, so `.murdock` uses **all supported boards**
instead of the quickbuild list; and a push carries no base commit, so change
detection is skipped and **all applications** are built:

```
$ ./scripts/poc-trigger-mergequeue.sh
[discovery] 171798 compile, 0 test, 1 static job(s)
```

That is the whole suite. Two knobs keep a single-node PoC manageable:

- `POC_DISCOVERY_JOBS` (default 8) parallelises the per-app board enumeration
  (Murdock distributes this over its worker fleet);
- `POC_MAX_DISPATCH` (default 0 = unlimited) caps how many jobs are actually
  dispatched — set it low for local experiments.

## Gates (mirroring Murdock)

- **skip keywords** (`ci_skip`, `murdock_skip`, `[ci skip]`) → no build
- **PR without `CI: ready for build`** → no build (waiting)
- **push branch not in `.murdock.yml` `push.branches`** (`staging`, `trying`,
  `gh-readonly-queue/`) → no build
- **merge-queue branch** (`gh-readonly-queue/…`) → full build
- **`CI: full build`** label → full build; **`CI: run tests`** → hardware tests

## Implementation notes / gotchas

- The extension cannot enumerate the job set (10 s timeout), hence the
  dispatcher-in-a-job design.
- The dispatcher runs the real `.murdock get_jobs` with a `dwqc` shim that
  executes each job generator locally and collects the resulting commands.
- `dispatch.py` maps Woodpecker's `CI_*` env onto `.murdock`'s (`CI_BUILD_BRANCH`,
  `CI_BASE_COMMIT` via `git merge-base` against the PR target branch,
  `CI_PULL_LABELS`).
- Woodpecker substitutes `${VAR}` in pipeline YAML **before** parsing, so all
  shell logic lives in base64-embedded scripts to keep the YAML valid.
- `wp_token` must be allowed for the `pull_request` event
  (`woodpecker-cli repo secret add --event pull_request …`).
- Dispatched pipelines target the PR's **source branch** (Woodpecker's
  `pipeline create` has no commit field), so same-repo PRs build the PR head.

## Gaps vs Murdock

- one Woodpecker pipeline per Murdock job still isn't a *single* forge status /
  sticky PR comment (Woodpecker reports the pipeline status; murfrog's tabs and
  per-application grouping are approximated by workflow names, not a custom UI)
- `dwq`-style incremental result aggregation / `reporter.py` (the UI updates as
  workflows finish rather than streaming counts)
- `git-cache` prefetching / `dwq`-style merge-branch cleanup (merge branches
  pushed by the dispatcher accumulate in the repo; Murdock deletes them)
- the Murdock REST API / `murfrog` UI and sticky PR comments
- `fasttrack` priority queues and `maxfail`/`CI: no fast fail` cancellation
  semantics (the label is read but Woodpecker has no global maxfail)
- hardware-in-the-loop: test jobs are generated and board-labelled, but the PoC
  has no board agents (`TEST_BOARDS_AVAILABLE` is empty)
