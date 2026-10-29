#!/usr/bin/env bash
#
# Minimal Murdock job script for the local stack.
#
# Murdock runs this script inside the job work directory and streams stdout to
# the job output. The job result is the script exit code.
set -euo pipefail

echo "-- Murdock local demo job"
echo "-- Working directory: $(pwd)"
echo "-- Job UID: ${CI_JOB_UID:-<unset>}"
echo "-- Commit: ${CI_BUILD_COMMIT:-${CI_PULL_COMMIT:-<unset>}}"
echo

for step in 1 2 3; do
  echo "step ${step}/3"
  sleep 1
done

echo "done"
