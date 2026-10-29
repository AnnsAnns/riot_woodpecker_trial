#!/usr/bin/env bash
# Apply, check, or revert submodule patches.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SUBMODULE="${SUBMODULE:-murdock}"
MODE="${1:-apply}"
PATCH_DIR="$ROOT/patches/$SUBMODULE"

case "$MODE" in
  apply|check|revert) ;;
  *)
    echo "usage: $0 [apply|check|revert]" >&2
    exit 1
    ;;
esac

if [ ! -d "$ROOT/$SUBMODULE" ]; then
  echo "submodule not found: $SUBMODULE" >&2
  exit 1
fi

shopt -s nullglob
patches=("$PATCH_DIR"/*.patch)
if [ ${#patches[@]} -eq 0 ]; then
  echo "no patches in $PATCH_DIR" >&2
  exit 1
fi

for patch in "${patches[@]}"; do
  echo "$MODE $(basename "$patch")"
  case "$MODE" in
    apply) git -C "$ROOT/$SUBMODULE" apply "$patch" ;;
    check) git -C "$ROOT/$SUBMODULE" apply --check "$patch" ;;
    revert) git -C "$ROOT/$SUBMODULE" apply --reverse "$patch" ;;
  esac
done
