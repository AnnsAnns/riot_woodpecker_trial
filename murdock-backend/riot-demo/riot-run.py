#!/usr/bin/env python3
"""Run a RIOT .murdock job and aggregate its results for a local Murdock job.

The wrapper runs inside the job container. It:
1. clones the mounted RIOT checkout into the job work directory,
2. discovers jobs with the real ./.murdock get_jobs using a small dwqc shim,
3. runs compile, test, and static-test commands,
4. sends progress to Murdock,
5. writes result.json, builds.json, tests.json, stats.json, and per-target logs.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

WORK = Path.cwd()
RIOT = WORK / "RIOT"
BASE_URL = os.environ.get("CI_BASE_URL", "http://localhost:8000").rstrip("/")
JOB_UID = os.environ["CI_JOB_UID"]
JOB_TOKEN = os.environ["CI_JOB_TOKEN"]
APPS = os.environ.get(
    "RIOT_DEMO_APPS", r"^(examples/basic/hello-world|tests/sys/shell)$"
)
BOARDS = os.environ.get("RIOT_DEMO_BOARDS", "native64 samr21-xpro")
TEST_BOARD = os.environ.get("RIOT_DEMO_TEST_BOARD", "native64")
MAX_FAILURES = 20

DWQC_SHIM = r"""#!/usr/bin/env python3
import os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

args = sys.argv[1:]
template = args[-1] if args else ""
stdin_mode = "-s" in args or "--stdin" in args

data = ""
if not sys.stdin.isatty():
    data = sys.stdin.read()
lines = [line for line in data.splitlines() if line.strip()]


def run_one(line):
    cmd = template
    for index, field in enumerate(line.split(" ")):
        cmd = cmd.replace("${%d}" % (index + 1), field)
    cmd = cmd.replace("${0}", line)
    subprocess.run(cmd, shell=True)


if stdin_mode and lines:
    workers = int(os.environ.get("RIOT_DISCOVERY_JOBS", "4") or 4)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        list(pool.map(run_one, lines))
elif template:
    subprocess.run(template, shell=True)
"""

LOCALJOB_SHIM = r"""#!/usr/bin/env python3
import sys

# The compile step calls dwq-localjob for native tests. The demo runs tests as
# separate run_test jobs, so skip the inline copy here.
print("dwq-localjob: inline test skipped", file=sys.stderr)
sys.exit(0)
"""

TARGET_RE = re.compile(
    r"\./\.murdock (compile|run_test) ([^ ]+) ([^:]+):([^ ]+)"
)


def log(*args: object) -> None:
    print("[riot-run]", *args, flush=True)


def send_status(state: str, **extra: object) -> None:
    payload = {"status": {"status": state, **extra}}
    request = urllib.request.Request(
        f"{BASE_URL}/job/{JOB_UID}/status",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": JOB_TOKEN,
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            response.read()
    except Exception as exc:  # noqa: BLE001
        log("status update failed:", exc)


def write_shims() -> Path:
    shim_dir = Path(tempfile.mkdtemp(prefix="riot-shims-"))
    for name, content in (("dwqc", DWQC_SHIM), ("dwq-localjob", LOCALJOB_SHIM)):
        path = shim_dir / name
        path.write_text(content)
        path.chmod(0o755)
    return shim_dir


def prepare_riot() -> None:
    if RIOT.exists():
        shutil.rmtree(RIOT)
    clone = subprocess.run(
        ["git", "clone", "--shared", "/riot", str(RIOT)],
        capture_output=True,
        text=True,
    )
    if clone.returncode != 0:
        log("git clone failed, copying RIOT without .git")
        shutil.copytree("/riot", RIOT, ignore=shutil.ignore_patterns(".git"))
    (RIOT / ".murdock").chmod(0o755)


def job_env(shim_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "APPS": APPS,
            "BOARDS": BOARDS,
            "FULL_BUILD": "1",
            "QUICK_BUILD": "0",
            "NIGHTLY": "0",
            "RUN_TESTS": "0",
            "STATIC_TESTS": "0",
            "ENABLE_TEST_CACHE": "0",
            # An unknown board disables the LLVM extra builds.
            "TEST_BOARDS_LLVM_COMPILE": "none",
            "CI_BUILD_BRANCH": "local-demo",
            "CI_MURDOCK_PROJECT": "local",
            "RIOT_CI_BUILD": "1",
            "CC_NOCOLOR": "1",
            "PATH": str(shim_dir) + os.pathsep + env.get("PATH", ""),
        }
    )
    return env


def discover(env: dict[str, str]) -> list[str]:
    log("discovering jobs with ./.murdock get_jobs")
    proc = subprocess.run(
        ["./.murdock", "get_jobs"],
        cwd=RIOT,
        env=env,
        text=True,
        capture_output=True,
    )
    if proc.stdout:
        print(proc.stdout, end="", flush=True)
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr, flush=True)
    if proc.returncode != 0:
        raise RuntimeError(f".murdock get_jobs failed with {proc.returncode}")

    commands = [
        line.strip()
        for line in proc.stdout.splitlines()
        if line.strip().startswith("./.murdock ")
    ]

    # Add explicit native test jobs. The real .murdock runs these inline with
    # dwq-localjob. Separate jobs make the test results visible in murfrog.
    for app in ("examples/basic/hello-world", "tests/sys/shell"):
        if (RIOT / app).is_dir():
            command = f"./.murdock run_test {app} {TEST_BOARD}:gnu"
            if command not in commands:
                commands.append(command)
    return commands


def output_path(command: str) -> Path:
    match = TARGET_RE.search(command)
    if match:
        kind, app, board, toolchain = match.groups()
        folder = "builds" if kind == "compile" else "tests"
        path = WORK / "output" / folder / app / f"{board}:{toolchain}.txt"
    else:
        name = command.split()[-1].strip("/")
        path = WORK / "output" / f"{name}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def failure_entry(command: str, runtime: float) -> dict[str, object]:
    match = TARGET_RE.search(command)
    if not match:
        return {}
    _, app, board, toolchain = match.groups()
    return {
        "application": app,
        "target": board,
        "toolchain": toolchain,
        "worker": "local",
        "runtime": round(runtime, 2),
    }


def run_command(command: str, env: dict[str, str]) -> dict[str, object]:
    log("running", command)
    shell_command = command
    if command.startswith("./.murdock run_test"):
        match = TARGET_RE.search(command)
        if match:
            _, app, board, toolchain = match.groups()
            # run_test expects the compile output in build/. A separate test
            # job does not have it, so build once before the test.
            shell_command = (
                f'BINDIR="$(pwd)/build" make -C{app} '
                f"BOARD={board} TOOLCHAIN={toolchain} all && {command}"
            )
    started = time.time()
    proc = subprocess.Popen(
        shell_command,
        cwd=RIOT,
        env=env,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="", flush=True)
        lines.append(line)
    returncode = proc.wait()
    runtime = time.time() - started
    output = "".join(lines)
    output_path(command).write_text(output)
    return {
        "result": {
            "status": returncode,
            "worker": "local",
            "runtime": runtime,
            "output": output,
            "body": {"command": command},
        }
    }


def write_result_files() -> None:
    script_dir = Path("/opt/murdock-scripts")
    for name in ("process_result.py", "common.py"):
        shutil.copy(script_dir / name, WORK / name)
    proc = subprocess.run(
        [sys.executable, "process_result.py"],
        cwd=WORK,
        env={**os.environ, "output_dir": str(WORK)},
        capture_output=True,
        text=True,
    )
    if proc.stdout:
        print(proc.stdout, end="", flush=True)
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr, flush=True)
    if proc.returncode != 0:
        log("process_result.py failed", proc.returncode)


def main() -> int:
    log("work directory", WORK)
    send_status("preparing")
    prepare_riot()
    shim_dir = write_shims()
    env = job_env(shim_dir)
    commands = discover(env)
    if not commands:
        log("no commands discovered")
        send_status("finished", total=0, passed=0, failed=0)
        return 1

    log(f"discovered {len(commands)} jobs")
    passed = 0
    failed = 0
    results: list[dict[str, object]] = []
    failed_builds: list[dict[str, object]] = []
    failed_tests: list[dict[str, object]] = []

    for index, command in enumerate(commands, start=1):
        send_status(
            "working",
            total=len(commands),
            passed=passed,
            failed=failed,
            eta=str(len(commands) - index + 1),
        )
        result = run_command(command, env)
        results.append(result)
        state = result["result"]["status"]  # type: ignore[index]
        runtime = result["result"]["runtime"]  # type: ignore[index]
        if state == 0:
            passed += 1
        else:
            failed += 1
            entry = failure_entry(command, float(runtime))  # type: ignore[arg-type]
            if entry:
                if command.startswith("./.murdock run_test"):
                    failed_tests.append(entry)
                else:
                    failed_builds.append(entry)
        send_status(
            "working",
            total=len(commands),
            passed=passed,
            failed=failed,
            eta=str(len(commands) - index),
            failed_builds=failed_builds[:MAX_FAILURES],
            failed_tests=failed_tests[:MAX_FAILURES],
        )

    (WORK / "result.json").write_text(json.dumps(results, indent=2))
    write_result_files()
    send_status(
        "finished",
        total=len(commands),
        passed=passed,
        failed=failed,
        eta="0",
        failed_builds=failed_builds[:MAX_FAILURES],
        failed_tests=failed_tests[:MAX_FAILURES],
    )
    log("done", f"passed={passed}", f"failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        log("fatal:", repr(exc))
        send_status("errored")
        sys.exit(1)
