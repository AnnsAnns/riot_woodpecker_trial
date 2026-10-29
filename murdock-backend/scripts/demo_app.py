"""Murdock demo app: serve the API and schedule one RIOT job on startup."""

import asyncio
import os
from pathlib import Path

import uvicorn

from murdock.config import MurdockSettings, TaskSettings
from murdock.job import MurdockJob
from murdock.main import app, murdock
from murdock.models import CommitModel


def read_git_head() -> str:
    """Read the RIOT commit SHA without a git binary in the API image."""
    git_dir = Path("/riot/.git")
    try:
        head = (git_dir / "HEAD").read_text().strip()
        if head.startswith("ref: "):
            ref = head[5:]
            ref_file = git_dir / ref
            if ref_file.exists():
                return ref_file.read_text().strip()
            packed = git_dir / "packed-refs"
            if packed.exists():
                for line in packed.read_text().splitlines():
                    if line.endswith(" " + ref):
                        return line.split()[0]
        return head
    except Exception:
        return "0" * 40


async def schedule_demo() -> None:
    await asyncio.sleep(3)
    sha = os.environ.get("RIOT_SHA") or read_git_head()
    tree = os.environ.get("RIOT_TREE") or sha
    config = MurdockSettings(
        env={
            "RIOT_DEMO_APPS": r"^(examples/basic/hello-world|tests/sys/shell)$",
            "RIOT_DEMO_BOARDS": "native64 samr21-xpro",
            "RIOT_DEMO_TEST_BOARD": "native64",
        },
        tasks=[
            TaskSettings(
                name="RIOT builds and tests",
                image="riotbuild-murdock-demo:local",
                command="python3 /usr/local/bin/riot-run.py",
            )
        ],
        artifacts=[
            "output.txt",
            "builds.json",
            "tests.json",
            "stats.json",
            "build_failures.json",
            "test_failures.json",
        ],
    )
    job = MurdockJob(
        CommitModel(
            sha=sha,
            tree=tree,
            message="local RIOT Murdock demo",
            author="local",
        ),
        ref="refs/heads/local-demo",
        config=config,
        trigger="api (manual)",
    )
    await murdock.schedule_job(job)
    print(f"[demo] scheduled job {job.uid}", flush=True)


@app.on_event("startup")
async def start_demo() -> None:
    if os.environ.get("RIOT_DEMO") == "1":
        asyncio.create_task(schedule_demo())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
