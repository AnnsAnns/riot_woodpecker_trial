#!/usr/bin/env bash
# Tear down the Phase 3 PoC stack.
#
#   ./scripts/poc-down.sh        # stop containers, keep volumes
#   ./scripts/poc-down.sh -v     # also remove volumes and local credentials
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose -f docker-compose.poc.yml --env-file .env.poc down "$@"
if [[ " $* " == *" -v "* ]]; then
  # Forgejo data is gone, so the OAuth app + session token are stale.
  rm -f .env.poc .token
fi
