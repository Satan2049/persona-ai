#!/usr/bin/env bash
# Build the Persona AI Python sidecar with PyInstaller (Linux / macOS).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/apps/backend"
SPEC="$ROOT/apps/desktop/sidecar/persona-backend.spec"
DIST="$ROOT/apps/desktop/sidecar/dist"
BINARIES="$ROOT/apps/desktop/src-tauri/binaries"
TAURI_DIR="$ROOT/apps/desktop/src-tauri"

TRIPLE="$(rustc --print host-tuple | tr -d '\r')"
if [[ -z "$TRIPLE" ]]; then
  echo "Could not determine Rust host triple (rustc --print host-tuple)." >&2
  exit 1
fi

SIDECAR_BUNDLED="$BINARIES/persona-backend-$TRIPLE"

cd "$BACKEND"

if [[ -x ".venv/bin/python" ]]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python3"
fi

"$PYTHON" -m pip install -r requirements-dev.txt
"$PYTHON" -m PyInstaller "$SPEC" --clean --noconfirm \
  --distpath "$DIST" \
  --workpath "$ROOT/apps/desktop/sidecar/build"

BUILT="$DIST/persona-backend"
if [[ ! -f "$BUILT" ]]; then
  # Some PyInstaller versions keep the .exe suffix even on Unix when the spec names it that way
  if [[ -f "$DIST/persona-backend.exe" ]]; then
    BUILT="$DIST/persona-backend.exe"
  else
    echo "PyInstaller output missing under $DIST" >&2
    ls -la "$DIST" || true
    exit 1
  fi
fi

mkdir -p "$BINARIES"
cp -f "$BUILT" "$SIDECAR_BUNDLED"
chmod +x "$SIDECAR_BUNDLED"
echo "Sidecar ready: $SIDECAR_BUNDLED"

for profile in debug release; do
  target_dir="$TAURI_DIR/target/$profile"
  if [[ -d "$target_dir" ]]; then
    cp -f "$BUILT" "$target_dir/persona-backend"
    chmod +x "$target_dir/persona-backend"
    echo "Copied sidecar -> target/$profile/persona-backend"
  fi
done
