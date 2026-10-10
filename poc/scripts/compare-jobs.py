#!/usr/bin/env python3
"""
Compare Murdock's job set with a dispatched Woodpecker pipeline's job set.

For a given Woodpecker pipeline (started by the dispatcher), this:
  1. reads the pipeline's `MURDOCK_BATCH` (what Woodpecker will run), and
  2. clones the exact ref the pipeline builds and runs the *real*
     `.murdock get_jobs` on it (what Murdock would run),
then diffs the two job sets.

They must be identical. Any difference is a regression in the bridge.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
POC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(POC, "config-extension"))
import dispatch  # noqa: E402


def env():
    e = {}
    with open(os.path.join(POC, ".env.poc")) as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                e[k] = v
    return e


def api(path, token):
    req = urllib.request.Request(f"http://localhost:8000{path}",
                                 headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def norm(jobs):
    return sorted((j["kind"], j.get("app", ""), j.get("board", ""),
                   j.get("toolchain", "")) for j in jobs)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pipeline", type=int, help="Woodpecker pipeline number")
    ap.add_argument("--repo-id", type=int, default=1)
    args = ap.parse_args()

    token = open(os.path.join(POC, ".token")).read().strip()
    e = env()
    admin, pw = e["POC_FORGEJO_ADMIN"], e["POC_FORGEJO_ADMIN_PASSWORD"]

    p = api(f"/api/repos/{args.repo_id}/pipelines/{args.pipeline}", token)
    v = p.get("variables") or {}
    if "MURDOCK_BATCH" not in v:
        sys.exit(f"pipeline {args.pipeline} has no MURDOCK_BATCH")
    woodpecker = norm(json.loads(v["MURDOCK_BATCH"]))
    ref = v.get("MURDOCK_REF") or e.get("POC_DEFAULT_REF", "refs/heads/master")
    print(f"pipeline {args.pipeline}: {p['message']!r} ref={ref}")

    # Murdock side: real `.murdock get_jobs` on the same ref
    tmp = tempfile.mkdtemp(prefix="cmp-")
    clone = os.path.join(tmp, "RIOT")
    subprocess.run(["git", "clone", "--quiet", "--no-checkout",
                    f"http://{admin}:{pw}@localhost:3000/{admin}/RIOT.git", clone],
                   check=True)
    subprocess.run(["git", "-C", clone, "fetch", "--quiet", "--no-tags",
                    "origin", ref], check=True)
    subprocess.run(["git", "-C", clone, "checkout", "--quiet", "FETCH_HEAD"],
                   check=True)
    os.environ["CI_BUILD_BRANCH"] = e.get("POC_BRANCH", "master")
    os.environ["CI_PIPELINE_EVENT"] = e.get("POC_EVENT", "pull_request")
    os.environ["CI_COMMIT_TARGET_BRANCH"] = e.get("POC_BRANCH", "master")
    # let murdock_env() compute CI_BASE_COMMIT the same way the dispatcher does
    os.environ.pop("CI_BASE_COMMIT", None)
    murdock = norm(dispatch.discover_jobs(clone))

    print(f"woodpecker jobs: {len(woodpecker)}   murdock jobs: {len(murdock)}")
    if woodpecker == murdock:
        print("IDENTICAL ✓")
        return 0
    only_wp = [j for j in woodpecker if j not in murdock]
    only_mu = [j for j in murdock if j not in woodpecker]
    print(f"only in Woodpecker ({len(only_wp)}):")
    for j in only_wp[:20]:
        print("   ", j)
    print(f"only in Murdock ({len(only_mu)}):")
    for j in only_mu[:20]:
        print("   ", j)
    return 1


if __name__ == "__main__":
    sys.exit(main())
