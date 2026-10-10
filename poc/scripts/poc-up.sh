#!/usr/bin/env bash
#
# Bootstrap the Phase 3 PoC: Forgejo + Woodpecker server/agent + the
# Murdock-compatible configuration extension, then log in headlessly and
# activate the RIOT repo so webhooks start pipelines.
#
# Idempotent-ish: safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/.."   # -> poc/

RIOT_SRC="${POC_RIOT_SRC:-$PWD/../RIOT}"
COMPOSE=(docker compose -f docker-compose.poc.yml --env-file .env.poc)

log() { printf '\n=== %s ===\n' "$*"; }
reload_env() { set -a; . ./.env.poc; set +a; }
wp() { woodpecker-cli --server http://localhost:8000 --token "$(cat .token)" "$@"; }

# --- 0. env file -----------------------------------------------------------
if [ ! -f .env.poc ]; then
  cat > .env.poc <<EOF
POC_FORGEJO_ADMIN=pocadmin
POC_FORGEJO_ADMIN_PASSWORD=pocpassword123
POC_FORGEJO_ADMIN_EMAIL=pocadmin@example.invalid
POC_AGENT_SECRET=$(head -c 24 /dev/urandom | base64 | tr -d '/+=')
POC_UID=$(id -u)
POC_GID=$(id -g)
POC_BOOTSTRAP_IMAGE=riotbuild-cached:poc
POC_JOB_IMAGE=riotbuild-cached:poc
POC_FORGEJO_OAUTH_ID=
POC_FORGEJO_OAUTH_SECRET=
EOF
fi
reload_env

FJ_API="http://localhost:3000/api/v1"
FJ_AUTH=(-u "$POC_FORGEJO_ADMIN:$POC_FORGEJO_ADMIN_PASSWORD")
REPO_URL="http://$POC_FORGEJO_ADMIN:$POC_FORGEJO_ADMIN_PASSWORD@localhost:3000/$POC_FORGEJO_ADMIN/RIOT.git"

# --- 0b. images ------------------------------------------------------------
if ! docker image inspect riot/riotbuild:latest >/dev/null 2>&1; then
  log "pulling riot/riotbuild:latest (~13 GB)"
  docker pull riot/riotbuild:latest
fi
if ! docker image inspect riotbuild-lite:poc >/dev/null 2>&1; then
  log "building riotbuild-lite:poc"
  docker build -t riotbuild-lite:poc "$PWD/riotbuild-lite"
fi
if ! docker image inspect riotbuild-cached:poc >/dev/null 2>&1; then
  log "building riotbuild-cached:poc"
  docker build -t riotbuild-cached:poc "$PWD/riotbuild-cached"
fi

# --- 1. Forgejo + extension ------------------------------------------------
log "starting Forgejo + config-extension"
"${COMPOSE[@]}" up -d forgejo config-extension

log "waiting for Forgejo"
for _ in $(seq 1 60); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' -m 5 "$FJ_API/version" || true)" = 200 ] && break
  sleep 2
done
curl -s "$FJ_API/version"; echo

# --- 2. admin user ---------------------------------------------------------
if [ "$(curl -s -o /dev/null -w '%{http_code}' "${FJ_AUTH[@]}" "$FJ_API/user" || true)" != 200 ]; then
  log "creating admin user"
  docker exec -u git poc-forgejo forgejo admin user create \
    --username "$POC_FORGEJO_ADMIN" --password "$POC_FORGEJO_ADMIN_PASSWORD" \
    --email "$POC_FORGEJO_ADMIN_EMAIL" --admin --must-change-password=false
fi

# --- 3. repo ---------------------------------------------------------------
log "ensuring repo exists"
curl -s "${FJ_AUTH[@]}" -X POST "$FJ_API/user/repos" \
  -H 'Content-Type: application/json' \
  -d '{"name":"RIOT","auto_init":false,"default_branch":"master"}' \
  -o /dev/null || true

# --- 4. push RIOT ----------------------------------------------------------
if ! git ls-remote "$REPO_URL" 2>/dev/null | grep -q refs/heads/master; then
  log "pushing RIOT into Forgejo (full clone of $RIOT_SRC)"
  tmp="$(mktemp -d)"
  git clone --quiet "$RIOT_SRC" "$tmp/RIOT"
  git -C "$tmp/RIOT" remote set-url origin "$REPO_URL"
  git -C "$tmp/RIOT" push --quiet origin master
  rm -rf "$tmp"
fi

# --- 5. OAuth application --------------------------------------------------
# Woodpecker builds the OAuth redirect from WOODPECKER_HOST
# (http://woodpecker-server:8000); host-side tooling reaches the same server at
# localhost:8000. Register both so either works.
if [ -z "${POC_FORGEJO_OAUTH_ID:-}" ]; then
  log "creating Forgejo OAuth application"
  curl -s "${FJ_AUTH[@]}" -X POST "$FJ_API/user/applications/oauth2" \
    -H 'Content-Type: application/json' \
    -d '{"name":"woodpecker","redirect_uris":["http://woodpecker-server:8000/authorize","http://localhost:8000/authorize"],"confidential_client":true}' \
    -o /tmp/poc-oauth.json
  CID="$(python3 -c 'import json;print(json.load(open("/tmp/poc-oauth.json"))["client_id"])')"
  CSEC="$(python3 -c 'import json;print(json.load(open("/tmp/poc-oauth.json"))["client_secret"])')"
  sed -i "s/^POC_FORGEJO_OAUTH_ID=.*/POC_FORGEJO_OAUTH_ID=$CID/" .env.poc
  sed -i "s/^POC_FORGEJO_OAUTH_SECRET=.*/POC_FORGEJO_OAUTH_SECRET=$CSEC/" .env.poc
  reload_env
fi

# --- 5b. Forgejo token for the dispatcher to push merge commits -------------
if [ -z "${POC_FORGEJO_TOKEN:-}" ]; then
  log "creating Forgejo API token (write:repository)"
  curl -s "${FJ_AUTH[@]}" -X POST "$FJ_API/users/$POC_FORGEJO_ADMIN/tokens" \
    -H 'Content-Type: application/json' \
    -d '{"name":"poc-ci-merge","scopes":["write:repository"]}' \
    -o /tmp/poc-fj-token.json
  FJTOK="$(python3 -c 'import json;print(json.load(open("/tmp/poc-fj-token.json"))["sha1"])')"
  echo "POC_FORGEJO_TOKEN=$FJTOK" >> .env.poc
  reload_env
fi

# --- 6. Woodpecker server + agent -----------------------------------------
log "starting Woodpecker server + agent"
"${COMPOSE[@]}" up -d woodpecker-server woodpecker-agent

log "waiting for Woodpecker server"
for _ in $(seq 1 60); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' -m 5 http://localhost:8000/ || true)" = 200 ] && break
  sleep 2
done

# --- 7. headless login -> token -------------------------------------------
log "logging in via Forgejo OAuth"
python3 scripts/forgejo_login.py > .token
echo "token acquired ($(cut -c1-12 .token)...)"

# --- 8. activate the repo --------------------------------------------------
log "activating repo"
REPO_FORGE_ID="$(curl -s "${FJ_AUTH[@]}" "$FJ_API/repos/$POC_FORGEJO_ADMIN/RIOT" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')"
wp repo add "$REPO_FORGE_ID" || true
wp repo ls || true

# secret used by the bootstrap dispatcher to start per-job pipelines. It must
# be allowed for the pull_request event, otherwise Woodpecker refuses it.
log "configuring dispatcher token secret"
wp repo secret add --repository "$POC_FORGEJO_ADMIN/RIOT" --name wp_token \
  --value "$(cat .token)" \
  --event push --event pull_request --event pull_request_metadata \
  --event pull_request_closed --event manual --event tag || true

# token used by the dispatcher to push the PR merge commit (Murdock's cache_repo)
log "configuring dispatcher forgejo token secret"
wp repo secret add --repository "$POC_FORGEJO_ADMIN/RIOT" --name forgejo_token \
  --value "${POC_FORGEJO_TOKEN:-}" \
  --event push --event pull_request --event pull_request_metadata \
  --event pull_request_closed --event manual --event tag || true

log "done"
echo "Woodpecker UI: http://localhost:8000   Forgejo UI: http://localhost:3000"
echo "Trigger a build with: ./scripts/poc-trigger.sh"
