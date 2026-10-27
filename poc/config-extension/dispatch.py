#!/usr/bin/env python3
"""
Murdock-compatible job discovery + dispatch for Woodpecker.

This is the faithful analogue of RIOT's `murdock-scripts/build.sh` +
`.murdock get_jobs`: it runs the **real** `.murdock get_jobs` (with a stubbed
`dwqc` that captures the job list instead of submitting to the disque queue)
and then starts one Woodpecker pipeline per job. Woodpecker pipelines are the
replacement for `dwq` jobs.

Running the real `.murdock` guarantees the job set matches Murdock exactly:
quickbuild vs full build, merge-queue full builds, `can_fast_ci_run` change
detection, labels, all supported boards and toolchains.

The module is self-contained so the Woodpecker configuration extension can
embed it verbatim into a bootstrap workflow.

Standalone dry-run (no server needed):

    RIOT_DIR=/path/to/RIOT APPS="^tests/sys/shell$" python3 dispatch.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

# --------------------------------------------------------------------------
# Stub dwqc: instead of queueing a job on disque, run the "job generator"
# locally and print the resulting commands, which is what we want to collect.
# `.murdock get_compile_jobs` calls:
#   get_apps | dwqc ... -s "$0 get_app_board_toolchain_pairs ${1} $0 compile"
# and each generator invocation prints `./.murdock compile <app> <board>:<tc>`.
# --------------------------------------------------------------------------
DWQC_SHIM = r'''#!/usr/bin/env python3
import os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

args = sys.argv[1:]
template = args[-1] if args else ""
stdin_mode = "-s" in args or "--stdin" in args

data = ""
if not sys.stdin.isatty():
    data = sys.stdin.read()
lines = [l for l in data.splitlines() if l.strip()]


def run_one(line):
    cmd = template
    for i, field in enumerate(line.split(" ")):
        cmd = cmd.replace("${%d}" % (i + 1), field)
    cmd = cmd.replace("${0}", line)
    subprocess.run(cmd, shell=True)


if stdin_mode and lines:
    # enumerate per-app job sets in parallel (Murdock does this distributed)
    workers = int(os.environ.get("POC_DISCOVERY_JOBS", "8") or 8)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        list(ex.map(run_one, lines))
elif template:
    subprocess.run(template, shell=True)
'''


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def _env(name, default=""):
    return os.environ.get(name, default)


def _git(riot_dir, *args):
    return subprocess.run(["git", *args], cwd=riot_dir,
                          capture_output=True, text=True)


def _set_authed_remote(riot_dir):
    """Set origin to an authenticated URL (for pushing/deleting merge refs)."""
    token = _env("FORGEJO_TOKEN")
    clone_url = _env("CI_REPO_CLONE_URL")
    owner = _env("CI_REPO_OWNER")
    if token and clone_url:
        authed = clone_url.replace("://", f"://{owner}:{token}@", 1)
        _git(riot_dir, "remote", "set-url", "origin", authed)
        return True
    return False


def git_cache_clone(riot_dir):
    """Populate an empty workspace via git-cache (shared object cache)."""
    url = _env("CI_REPO_CLONE_URL")
    commit = _env("CI_COMMIT_SHA")
    if not url or not commit:
        return False
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    proc = subprocess.run(["git-cache", "clone", url, ".", "--commit", commit],
                          cwd=riot_dir, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        log(f"[clone] git-cache failed: {proc.stderr.strip()[:200]}")
        return False
    log(f"[clone] git-cache checkout of {commit[:7]} in {riot_dir}")
    return True


def cleanup_merge_branches(riot_dir, keep_ref):
    """Delete `murdock/build/*` branches older than POC_MERGE_TTL (Murdock
    deletes its worker branch after the build)."""
    ttl = int(_env("POC_MERGE_TTL", "3600") or 0)
    if ttl <= 0:
        return
    _set_authed_remote(riot_dir)
    out = _git(riot_dir, "ls-remote", "origin", "refs/heads/murdock/build/*")
    if out.returncode != 0:
        return
    now = time.time()
    removed = 0
    for line in out.stdout.splitlines():
        sha, ref = line.split(None, 1)
        ref = ref.strip()
        if ref == keep_ref:
            continue
        ct = _git(riot_dir, "log", "-1", "--format=%ct", sha).stdout.strip()
        if not ct:
            _git(riot_dir, "fetch", "--no-tags", "--depth", "1", "origin", sha)
            ct = _git(riot_dir, "log", "-1", "--format=%ct", sha).stdout.strip()
        try:
            age = now - int(ct)
        except (TypeError, ValueError):
            log(f"[cleanup] {ref}: no commit time ({ct!r}), skipping")
            continue
        log(f"[cleanup] {ref} age={int(age)}s keep={ref == keep_ref}")
        if age > ttl:
            p = _git(riot_dir, "push", "origin", "--delete", ref)
            if p.returncode == 0:
                removed += 1
            else:
                log(f"[cleanup] delete {ref} failed: {p.stderr.strip()[:160]}")
    if removed:
        log(f"[cleanup] removed {removed} old merge branch(es)")


def create_merge(riot_dir):
    """Reproduce murdock-scripts/build.sh's PR handling: merge the PR head into
    the *current* base branch head, push it, and build that merge commit.

    Returns (merge_sha, merge_ref) or None if this isn't a PR / the merge or
    push failed (in which case we fall back to building the PR head).
    """
    if _env("POC_MERGE", "1") == "0":
        return None
    if _env("CI_PIPELINE_EVENT") != "pull_request":
        return None
    base_branch = _env("CI_COMMIT_TARGET_BRANCH") or _env("CI_COMMIT_BRANCH")
    head = _env("CI_COMMIT_SHA")
    if not base_branch or not head:
        return None

    # make sure we have history (the bootstrap clone may be shallow)
    if _git(riot_dir, "rev-parse", "--is-shallow-repository").stdout.strip() == "true":
        _git(riot_dir, "fetch", "--unshallow", "--no-tags", "origin")

    _git(riot_dir, "fetch", "--no-tags", "origin", base_branch)
    base = _git(riot_dir, "rev-parse", "FETCH_HEAD").stdout.strip()
    _git(riot_dir, "fetch", "--no-tags", "origin", head)
    head_sha = _git(riot_dir, "rev-parse", "FETCH_HEAD").stdout.strip()
    if not base or not head_sha:
        log("[merge] could not resolve base/head")
        return None

    _git(riot_dir, "checkout", "-q", base)
    merge = _git(riot_dir, "merge", "--no-rerere-autoupdate", "--no-edit",
                 "--no-ff", head_sha)
    if merge.returncode != 0:
        log(f"[merge] merge failed, building head instead: {merge.stderr.strip()[:200]}")
        return None
    merge_sha = _git(riot_dir, "rev-parse", "HEAD").stdout.strip()
    ref = f"refs/heads/murdock/build/{merge_sha}"
    # authenticate the push (Murdock pushes to its `cache_repo`; we push to the
    # same forge repo using a scoped token supplied as a secret)
    _set_authed_remote(riot_dir)
    push = _git(riot_dir, "push", "-f", "origin", f"HEAD:{ref}")
    if push.returncode != 0:
        log(f"[merge] push failed, building head instead: {push.stderr.strip()[:200]}")
        return None
    log(f"[merge] {base[:7]} + {head_sha[:7]} -> {merge_sha[:7]} (pushed to {ref})")
    return merge_sha, ref


def murdock_env(riot_dir):
    """Map Woodpecker's CI_* environment onto the names `.murdock` expects."""
    env = os.environ.copy()
    env["CI_BUILD_BRANCH"] = env.get("CI_COMMIT_BRANCH") or \
        env.get("CI_COMMIT_TARGET_BRANCH", "")
    env["CI_PULL_LABELS"] = env.get("CI_COMMIT_PULL_REQUEST_LABELS", "")
    # For PRs the base is the target branch; Woodpecker exposes it as
    # CI_COMMIT_TARGET_BRANCH, falling back to CI_COMMIT_BRANCH.
    target = env.get("CI_COMMIT_TARGET_BRANCH") or env.get("CI_COMMIT_BRANCH")
    event = env.get("CI_PIPELINE_EVENT", "")
    log(f"[discovery] event={event!r} target={target!r} "
        f"source={env.get('CI_COMMIT_SOURCE_BRANCH')!r} sha={env.get('CI_COMMIT_SHA')!r}")
    if not env.get("CI_BASE_COMMIT") and target and event == "pull_request":
        try:
            shallow = subprocess.run(["git", "rev-parse", "--is-shallow-repository"],
                                     cwd=riot_dir, capture_output=True, text=True)
            if shallow.stdout.strip() == "true":
                subprocess.run(["git", "fetch", "--unshallow", "--no-tags", "origin"],
                               cwd=riot_dir, capture_output=True)
            fetch = subprocess.run(["git", "fetch", "--no-tags", "origin", target],
                                   cwd=riot_dir, capture_output=True, text=True)
            mb = subprocess.run(["git", "merge-base", "HEAD", f"origin/{target}"],
                                cwd=riot_dir, capture_output=True, text=True)
            log(f"[discovery] merge-base rc={mb.returncode} "
                f"out={mb.stdout.strip()!r} fetch_rc={fetch.returncode} "
                f"fetch_err={fetch.stderr.strip()[:200]!r}")
            if mb.returncode == 0 and mb.stdout.strip():
                env["CI_BASE_COMMIT"] = mb.stdout.strip()
        except Exception as exc:  # noqa: BLE001
            log(f"[discovery] merge-base failed: {exc!r}")
    return env


def discover_jobs(riot_dir):
    """Run the real `.murdock get_jobs` with a stubbed dwqc; return job list."""
    tmp = tempfile.mkdtemp(prefix="dwqc-shim-")
    shim = os.path.join(tmp, "dwqc")
    with open(shim, "w") as f:
        f.write(DWQC_SHIM)
    os.chmod(shim, os.stat(shim).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    env = murdock_env(riot_dir)
    # propagate the computed base commit so the dispatched jobs carry it
    if env.get("CI_BASE_COMMIT"):
        os.environ["CI_BASE_COMMIT"] = env["CI_BASE_COMMIT"]
    env["PATH"] = tmp + os.pathsep + env.get("PATH", "")
    env["RIOT_CI_BUILD"] = "1"

    log(f"[discovery] .murdock env: branch={env.get('CI_BUILD_BRANCH')!r} "
        f"base_commit={env.get('CI_BASE_COMMIT')!r} labels={env.get('CI_PULL_LABELS')!r}")
    log(f"[discovery] running ./.murdock get_jobs in {riot_dir}")
    proc = subprocess.run(["./.murdock", "get_jobs"], cwd=riot_dir, env=env,
                          capture_output=True, text=True)
    if proc.stderr.strip():
        for line in proc.stderr.splitlines():
            log("[.murdock] " + line)

    jobs = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        m = re.match(r"^\./\.murdock (compile|run_test) (\S+) (\S+):(\S+)$", line)
        if m:
            jobs.append({"kind": "compile" if m.group(1) == "compile" else "test",
                         "app": m.group(2), "board": m.group(3),
                         "toolchain": m.group(4)})
            continue
        if line.endswith(".murdock static_tests") or line == "./.murdock static_tests":
            jobs.append({"kind": "static"})
            continue
        if line:
            log(f"[discovery] (ignored output) {line}")

    comp = sum(1 for j in jobs if j["kind"] == "compile")
    test = sum(1 for j in jobs if j["kind"] == "test")
    nstatic = sum(1 for j in jobs if j["kind"] == "static")
    log(f"[discovery] {comp} compile, {test} test, {nstatic} static job(s)")
    return jobs


def compute_run_tests():
    explicit = _env("MURDOCK_RUN_TESTS")
    if explicit:
        return explicit
    nightly = _env("NIGHTLY", "0")
    labels = _env("CI_PULL_LABELS", "")
    if nightly == "1" or "CI: run tests" in labels:
        return "1"
    return "0"


def add_hardware_test_jobs(jobs):
    """Murdock dispatches hardware tests from within the compile job; we model
    them as separate jobs, but only for boards the cluster can actually test
    (TEST_BOARDS_AVAILABLE), and only when RUN_TESTS=1."""
    run_tests = compute_run_tests()
    available = set((_env("TEST_BOARDS_AVAILABLE") or "").split())
    if run_tests != "1" or not available:
        return jobs
    seen = set()
    extra = []
    for job in jobs:
        if job["kind"] != "compile":
            continue
        key = (job["app"], job["board"])
        if job["board"] in available and key not in seen:
            seen.add(key)
            extra.append({"kind": "test", "app": job["app"],
                          "board": job["board"], "toolchain": job["toolchain"]})
    if extra:
        log(f"[discovery] + {len(extra)} hardware test job(s)")
    return jobs + extra


# --------------------------------------------------------------------------
# Dispatch: one Woodpecker pipeline per job
# --------------------------------------------------------------------------

def murdock_title(env):
    commit = env.get("CI_COMMIT_SHA", "") or ""
    sha7 = commit[:7]
    ref = env.get("CI_COMMIT_REF", "") or ""
    event = env.get("CI_PIPELINE_EVENT", "")
    pr = env.get("CI_COMMIT_PULL_REQUEST", "")
    title = env.get("CI_COMMIT_TITLE", "") or ""
    if event == "pull_request" and pr:
        suffix = f": {title}" if title else ""
        return f"PR #{pr}{suffix} ({sha7})"
    if ref.startswith("refs/tags/"):
        return f"tag {ref[len('refs/tags/'):]} ({sha7})"
    if ref.startswith("refs/heads/"):
        return f"branch {ref[len('refs/heads/'):]} ({sha7})"
    return f"commit {sha7}"


def dispatch(jobs, dry_run=False):
    server = _env("WOODPECKER_SERVER_INTERNAL", "http://localhost:8000")
    token = _env("WP_TOKEN")
    repo = _env("CI_REPO")
    # pipeline branch: for PRs this is the target branch, which the UI shows by
    # default; the exact commit to build is carried in MURDOCK_REF.
    branch = _env("CI_COMMIT_BRANCH") or _env("CI_COMMIT_TARGET_BRANCH") or "master"
    ref = _env("CI_COMMIT_REF")
    commit = _env("CI_COMMIT_SHA")
    title = murdock_title(os.environ)

    if dry_run:
        for j in jobs:
            print(json.dumps(j))
        return

    if not token:
        raise RuntimeError("WP_TOKEN is not set; cannot dispatch pipelines")

    req = urllib.request.Request(
        f"{server}/api/repos/lookup/{urllib.parse.quote(repo)}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        repo_id = json.load(resp)["id"]
    log(f"[dispatch] repo {repo} -> id {repo_id}, branch {branch}, ref {ref}, "
        f"commit {commit}")

    common = {
        "MURDOCK_REF": ref,
        "MURDOCK_COMMIT": commit or "",
        "MURDOCK_BASE_COMMIT": _env("CI_BASE_COMMIT"),
        "MURDOCK_RUN_TESTS": compute_run_tests(),
        "MURDOCK_ENABLE_TEST_CACHE": _env("MURDOCK_ENABLE_TEST_CACHE", "1"),
        "MURDOCK_STATIC_TESTS": _env("MURDOCK_STATIC_TESTS", "0"),
        "MURDOCK_JOBS": _env("MURDOCK_JOBS", "4"),
        "MURDOCK_TITLE": title,
    }

    # Safety valve for local runs: a full (merge-queue) build is ~200k jobs.
    # 0 = unlimited (default); set POC_MAX_DISPATCH to cap what is dispatched.
    cap = int(_env("POC_MAX_DISPATCH", "0") or 0)
    if cap and len(jobs) > cap:
        log(f"[dispatch] POC_MAX_DISPATCH={cap}: dispatching {cap} of {len(jobs)} jobs")
        jobs = jobs[:cap]

    # Batch jobs into pipelines. Default: all jobs in one pipeline, so the
    # Woodpecker pipeline page lists every build/test (like a murfrog job).
    batch_size = int(_env("POC_BATCH_SIZE", "0") or 0) or max(len(jobs), 1)
    batches = [jobs[i:i + batch_size] for i in range(0, len(jobs), batch_size)]

    ok = 0
    for idx, batch in enumerate(batches):
        variables = dict(common)
        variables["MURDOCK_BATCH"] = json.dumps(batch, separators=(",", ":"))
        message = title if len(batches) == 1 else f"{title} [{idx + 1}/{len(batches)}]"
        body = json.dumps({"branch": branch, "message": message,
                           "variables": variables}).encode()
        req = urllib.request.Request(
            f"{server}/api/repos/{repo_id}/pipelines", data=body, method="POST",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp.read()
            ok += 1
        except urllib.error.HTTPError as exc:
            log(f"[dispatch] failed to start pipeline {message}: "
                f"{exc.code} {exc.read()!r}")
    log(f"[dispatch] started {ok}/{len(batches)} pipeline(s) with {len(jobs)} jobs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="print the job list instead of dispatching")
    parser.add_argument("--riot-dir", default=_env("RIOT_DIR") or os.getcwd())
    args = parser.parse_args()

    riot_dir = args.riot_dir
    # bootstrap clone via the shared git-cache (the Woodpecker clone step is
    # skipped for the bootstrap pipeline)
    if not os.path.isdir(os.path.join(riot_dir, ".git")):
        if not git_cache_clone(riot_dir):
            log("[clone] falling back to plain git clone")
            subprocess.run(["git", "clone", "--depth", "1",
                            _env("CI_REPO_CLONE_URL"), "."],
                           cwd=riot_dir, capture_output=True)

    merge = create_merge(riot_dir)
    if merge:
        merge_sha, merge_ref = merge
        os.environ["CI_COMMIT_SHA"] = merge_sha
        os.environ["CI_COMMIT_REF"] = merge_ref
    cleanup_merge_branches(riot_dir, os.environ.get("CI_COMMIT_REF", ""))
    jobs = discover_jobs(riot_dir)
    jobs = add_hardware_test_jobs(jobs)
    dispatch(jobs, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
