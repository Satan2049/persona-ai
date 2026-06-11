#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/apps/backend"
SPEC="$ROOT/apps/desktop/sidecar/persona-backend.spec"
DIST="$ROOT/apps/desktop/sidecar/dist"
BINARIES="$ROOT/apps/desktop/src-tauri/binaries"

cd "$BACKEND"
if [[ -x .venv/bin/python ]]; then
  PYTHON=.venv/bin/python
else
  PYTHON=python3
fi

"$PYTHON" -m pip install -r requirements-dev.txt
"$PYTHON" -m PyInstaller "$SPEC" --noconfirm --distpath "$DIST" --workpath "$ROOT/apps/desktop/sidecar/build"

mkdir -p "$BINARIES"
ARCH="$(uname -m)"
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
TRIPLE="${ARCH}-unknown-${OS}-gnu"
if [[ "$OS" == "darwin" ]]; then
  TRIPLE="${ARCH}-apple-darwin"
fi

cp "$DIST/persona-backend" "$BINARIES/persona-backend-$TRIPLE"
echo "Sidecar ready: $BINARIES/persona-backend-$TRIPLE"
