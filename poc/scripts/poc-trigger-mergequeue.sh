#!/usr/bin/env bash
#
# Simulate a GitHub merge-queue build: push to a `gh-readonly-queue/<base>/...`
# branch. Murdock treats these as full builds (QUICK_BUILD=0), so this should
# dispatch the entire test suite (all apps x all supported boards), not a
# quickbuild.
#
# NOTE: a real full build is ~200k jobs. Set POC_MAX_DISPATCH to cap it for
# local experiments (0 = unlimited).
set -euo pipefail
cd "$(dirname "$0")/.."   # -> poc/
set -a; . ./.env.poc; set +a

REPO_URL="http://$POC_FORGEJO_ADMIN:$POC_FORGEJO_ADMIN_PASSWORD@localhost:3000/$POC_FORGEJO_ADMIN/RIOT.git"
CLONE="${POC_MQ_CLONE:-$PWD/.mq-trigger}"
BASE="${POC_MQ_BASE:-master}"
BRANCH="gh-readonly-queue/$BASE/$(date +%s)"

if [ ! -d "$CLONE/.git" ]; then
  echo "cloning RIOT into $CLONE (first run)"
  git clone --quiet "$REPO_URL" "$CLONE"
fi
cd "$CLONE"
git config user.name  "poc-ci"
git config user.email "poc-ci@example.invalid"
git fetch --quiet origin "$BASE"
git checkout --quiet -B "$BRANCH" "origin/$BASE"

APP="${POC_PR_APP:-tests/sys/shell}"
STAMP="$(date +%s)"
printf '\nstatic volatile int poc_mq_%s = 1;\n' "$STAMP" >> "$APP/main.c"
git commit -qam "poc: merge-queue build $STAMP"
git push --quiet -f origin "$BRANCH"

echo "pushed merge-queue branch $BRANCH (change in $APP)"
