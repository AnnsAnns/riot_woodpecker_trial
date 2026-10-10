#!/usr/bin/env bash
#
# Create (or update) a pull request in Forgejo with a change to
# tests/sys/shell, add the "CI: ready for build" label, and push a commit so
# the PR is (re)built. This exercises the Murdock quickbuild path: change
# detection picks the changed app and dispatches it for the quickbuild boards.
set -euo pipefail
cd "$(dirname "$0")/.."   # -> poc/
set -a; . ./.env.poc; set +a

FJ="http://localhost:3000/api/v1"
AUTH=(-u "$POC_FORGEJO_ADMIN:$POC_FORGEJO_ADMIN_PASSWORD")
REPO_URL="http://$POC_FORGEJO_ADMIN:$POC_FORGEJO_ADMIN_PASSWORD@localhost:3000/$POC_FORGEJO_ADMIN/RIOT.git"
CLONE="${POC_PR_CLONE:-$PWD/.pr-trigger}"
BRANCH="${POC_PR_BRANCH:-poc-pr}"

if [ ! -d "$CLONE/.git" ]; then
  echo "cloning RIOT into $CLONE (first run)"
  git clone --quiet "$REPO_URL" "$CLONE"
fi
cd "$CLONE"
git config user.name  "poc-ci"
git config user.email "poc-ci@example.invalid"
git fetch --quiet origin master
git checkout --quiet -B "$BRANCH" origin/master

STAMP="$(date +%s)"
APP="${POC_PR_APP:-tests/sys/shell}"
printf '\nstatic volatile int poc_pr_%s = 1;\n' "$STAMP" >> "$APP/main.c"
git commit -qam "poc: PR change $STAMP ($APP)"
git push --quiet -f origin "$BRANCH"

# create the PR if it doesn't exist yet
if ! curl -s "${AUTH[@]}" "$FJ/repos/$POC_FORGEJO_ADMIN/RIOT/pulls?state=open" \
     | python3 -c "import sys,json; sys.exit(0 if any(p['head']['ref']=='$BRANCH' for p in json.load(sys.stdin)) else 1)"; then
  curl -s "${AUTH[@]}" -X POST "$FJ/repos/$POC_FORGEJO_ADMIN/RIOT/pulls" \
    -H 'Content-Type: application/json' \
    -d "{\"title\":\"poc pr\",\"head\":\"$BRANCH\",\"base\":\"master\"}" -o /dev/null
fi

# ensure the ready label exists and is set on the PR
curl -s "${AUTH[@]}" -X POST "$FJ/repos/$POC_FORGEJO_ADMIN/RIOT/labels" \
  -H 'Content-Type: application/json' \
  -d '{"name":"CI: ready for build","color":"#00ff00"}' -o /dev/null || true
PRNUM="$(curl -s "${AUTH[@]}" "$FJ/repos/$POC_FORGEJO_ADMIN/RIOT/pulls?state=open" \
  | python3 -c "import sys,json;print([p['number'] for p in json.load(sys.stdin) if p['head']['ref']=='$BRANCH'][0])")"
curl -s "${AUTH[@]}" -X POST "$FJ/repos/$POC_FORGEJO_ADMIN/RIOT/issues/$PRNUM/labels" \
  -H 'Content-Type: application/json' \
  -d '{"labels":["CI: ready for build"]}' -o /dev/null

echo "pushed PR #$PRNUM ($BRANCH) with 'CI: ready for build' label"
