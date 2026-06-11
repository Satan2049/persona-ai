#!/usr/bin/env bash
# Remove generated build artifacts and caches from the repo.
#
# Usage:
#   ./scripts/clean-temps.sh              # build outputs
#   ./scripts/clean-temps.sh --runtime    # also audio / RAG index
#   ./scripts/clean-temps.sh --deep       # also node_modules/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME=0
DEEP=0

for arg in "$@"; do
  case "$arg" in
    --runtime) RUNTIME=1 ;;
    --deep) DEEP=1 ;;
    -h|--help)
      echo "Usage: $0 [--runtime] [--deep]"
      exit 0
      ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

removed=0

remove_path() {
  local rel="$1"
  local full="$ROOT/$rel"
  if [[ -e "$full" ]]; then
    rm -rf "$full"
    echo "Removed $rel"
    removed=$((removed + 1))
  fi
}

clear_keep_gitkeep() {
  local rel="$1"
  local full="$ROOT/$rel"
  if [[ -d "$full" ]]; then
    find "$full" -mindepth 1 ! -name '.gitkeep' -delete 2>/dev/null || true
    touch "$full/.gitkeep"
    echo "Cleared $rel (kept .gitkeep)"
    removed=$((removed + 1))
  fi
}

for rel in \
  apps/desktop/sidecar/build \
  apps/desktop/sidecar/dist \
  apps/desktop/src-tauri/target \
  apps/desktop/src-tauri/gen \
  .pytest_cache .mypy_cache .ruff_cache \
  dist/release; do
  remove_path "$rel"
done

bin_dir="$ROOT/apps/desktop/src-tauri/binaries"
if [[ -d "$bin_dir" ]]; then
  find "$bin_dir" -type f ! -name '.gitkeep' -delete 2>/dev/null || true
  touch "$bin_dir/.gitkeep"
  echo "Cleared apps/desktop/src-tauri/binaries/*"
  removed=$((removed + 1))
fi

while IFS= read -r -d '' dir; do
  rel="${dir#$ROOT/}"
  echo "Removed $rel"
  rm -rf "$dir"
  removed=$((removed + 1))
done < <(find "$ROOT" -type d -name '__pycache__' -print0 2>/dev/null)

if [[ "$RUNTIME" -eq 1 ]]; then
  for rel in audio apps/backend/audio data/rag_index; do
    clear_keep_gitkeep "$rel"
  done
fi

if [[ "$DEEP" -eq 1 ]]; then
  for rel in node_modules apps/desktop/node_modules; do
    remove_path "$rel"
  done
fi

if [[ "$removed" -eq 0 ]]; then
  echo "Nothing to clean."
else
  echo "Done. ($removed area(s) cleaned)"
fi

echo "Kept: apps/backend/.venv, .env, piper_models/, piper/, source."
