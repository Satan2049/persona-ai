# Persona AI Desktop

Tauri 2 desktop shell for Persona AI. On launch the shell **automatically spawns** a **Python sidecar** (`persona-backend`) in the background, waits for `/health`, injects the API URL into the UI, and kills the process when the app exits. The UI opens in **voice conversation** first.

## Prerequisites

- [Node.js](https://nodejs.org/) 20+
- [Rust](https://www.rust-lang.org/tools/install)
- **Python 3.10–3.12** with `apps/backend` dependencies:

  ```bash
  cd apps/backend
  python -m venv .venv
  # Windows: .venv\Scripts\activate
  # Linux/macOS: source .venv/bin/activate
  pip install -r requirements-dev.txt
  ```

  Python 3.14 often breaks `pydantic_core` in the PyInstaller bundle.

## Build the sidecar

**Windows** (from repo root):

```powershell
npm run sidecar:build
```

**Linux / macOS:**

```bash
chmod +x scripts/build-sidecar.sh
./scripts/build-sidecar.sh
```

On Windows, `scripts/prepare-sidecar-env.ps1` copies `apps/backend/.env` into the sidecar bundle as `runtime.env`.

Output: `apps/desktop/src-tauri/binaries/persona-backend-<target-triple>[.exe]`

## Sync UI assets

```powershell
.\scripts\sync-desktop-ui.ps1
```

## Desktop build

```powershell
npm run desktop:build
```

Windows installer: `apps/desktop/src-tauri/target/release/bundle/nsis/`

CI builds Linux (AppImage/deb) and macOS (DMG) — see `.github/workflows/desktop-linux.yml` and `desktop-macos.yml`.

## Version

`1.3.2` — keep in sync with root `package.json`, `tauri.conf.json`, and `Cargo.toml`.
