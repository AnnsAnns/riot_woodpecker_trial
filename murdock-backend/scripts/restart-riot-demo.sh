#!/usr/bin/env bash
# Restart the API and schedule a new RIOT demo job.
set -euo pipefail
cd "$(dirname "$0")/.."

export RIOT_SHA="$(git -C ../RIOT rev-parse HEAD)"
export RIOT_TREE="$(git -C ../RIOT rev-parse 'HEAD^{tree}')"

docker compose -f docker-compose.yml -f docker-compose.riot-demo.yml up -d --force-recreate murdock
echo "Murdock API: http://localhost:8000/api"
echo "Murdock demo job SHA: ${RIOT_SHA}"
