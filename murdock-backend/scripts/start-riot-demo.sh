#!/usr/bin/env bash
# Start the local Murdock API with the RIOT demo job and Docker job mode.
set -euo pipefail
cd "$(dirname "$0")/.."

export RIOT_SHA="$(git -C ../RIOT rev-parse HEAD)"
export RIOT_TREE="$(git -C ../RIOT rev-parse 'HEAD^{tree}')"

docker compose -f docker-compose.yml -f docker-compose.riot-demo.yml up -d "$@"
echo "Murdock API: http://localhost:8000/api"
echo "RIOT job:    http://localhost:8000/jobs"
echo "Murdock demo job SHA: ${RIOT_SHA}"
