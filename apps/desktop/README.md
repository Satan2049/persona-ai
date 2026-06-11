# Persona AI Desktop

Tauri 2 desktop shell for Persona AI. The shell spawns a **Python sidecar** (`persona-backend`) that runs the same FastAPI backend used in development.

## Prerequisites

- [Node.js](https://nodejs.org/) 20+
- [Rust](https://www.rust-lang.org/tools/install)
- **Python 3.10–3.12** with `apps/backend` dependencies installed manually:

  ```bash
  cd apps/backend
  python -m venv .venv
  .venv\Scripts\activate
  pip install -r requirements-dev.txt
  ```

  Python 3.14 often breaks `pydantic_core` in the PyInstaller bundle.

## Build the sidecar

Install Python deps first (see above), then from the repository root:

```powershell
npm run sidecar:build
```

This installs `requirements-dev.txt` (via your configured pip index) and runs PyInstaller.

This produces `apps/desktop/src-tauri/binaries/persona-backend-<target-triple>.exe` (Windows).

## Generate icons

```bash
cd apps/desktop
npm install
npm run icons
```

Source artwork: `assets/icons/app-icon.svg` (exported to `app-icon-1024.png` via `scripts/export-app-icon.ps1`).

## Development

```bash
npm install
npm run sidecar:build
npm run desktop:dev
```

The window loads a splash page, starts the sidecar on an ephemeral port, waits for `/health`, then navigates to the bundled UI.

## Production build

```bash
npm run sidecar:build
npm run desktop:build
```

Installers are written under `apps/desktop/src-tauri/target/release/bundle/`.

## User data

The desktop app stores writable files under:

| Platform | Path |
|----------|------|
| Windows | `%APPDATA%\PersonaAI\` |
| macOS | `~/Library/Application Support/PersonaAI/` |
| Linux | `~/.local/share/PersonaAI/` |

Place Piper voice models in `%APPDATA%\PersonaAI\piper_models\` or configure `PIPER_MODELS_DIR` in **Settings** (saved to `%APPDATA%\PersonaAI\.env`).

Full layout: [docs/desktop-data-layout.md](../../docs/desktop-data-layout.md).
