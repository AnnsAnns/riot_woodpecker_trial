#!/usr/bin/env bash
#
# Push a small change to the RIOT repo in Forgejo to trigger a pipeline.
# The change is a non-comment addition so RIOT's change detection sees it.
set -euo pipefail
cd "$(dirname "$0")/.."   # -> poc/
set -a; . ./.env.poc; set +a

REPO_URL="http://$POC_FORGEJO_ADMIN:$POC_FORGEJO_ADMIN_PASSWORD@localhost:3000/$POC_FORGEJO_ADMIN/RIOT.git"
CLONE="${POC_TRIGGER_CLONE:-$PWD/.riot-trigger}"

if [ ! -d "$CLONE/.git" ]; then
  echo "cloning RIOT into $CLONE (first run, this takes a moment)"
  git clone --quiet "$REPO_URL" "$CLONE"
fi

cd "$CLONE"
git config user.name  "poc-ci"
git config user.email "poc-ci@example.invalid"
git fetch --quiet origin master
git checkout --quiet master
git reset --hard --quiet origin/master

MARKER="${POC_TRIGGER_APP:-tests/sys/shell}"
STAMP="$(date +%s)"
printf '\nstatic volatile int poc_trigger_%s = 1;\n' "$STAMP" >> "$MARKER/main.c"

git commit -qam "poc: trigger CI run $STAMP"
git push --quiet origin master
echo "pushed trigger commit to $MARKER ($STAMP)"
