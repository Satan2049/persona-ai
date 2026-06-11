# Contributing to Persona AI

Thank you for your interest in contributing. This project is a monorepo with a Python backend, static web UI, and Tauri desktop shell.

## Repository layout

```
persona-ai/
├── apps/
│   ├── backend/          # FastAPI API, RAG, Piper integration
│   └── desktop/          # Tauri shell + PyInstaller sidecar packaging
├── assets/               # Icons, screenshots, shared config
├── data/                 # FAQ corpus and generated RAG index
├── docs/                 # Design, trust, and deployment documentation
├── scripts/              # Build and dev helpers
└── ui/                   # Avatar chat frontend (served by the backend)
```

## Development setup

1. **Python backend**

   ```bash
   cd apps/backend
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   ```

2. **Start the API** (from repo root):

   ```bash
   scripts/start-backend.bat      # Windows
   ./scripts/start-backend.ps1    # PowerShell
   ```

3. **Desktop app** (optional):

   ```bash
   npm install
   npm run sidecar:build
   cd apps/desktop && npm run icons
   npm run desktop:dev
   ```

## Code guidelines

- Keep business logic in `apps/backend/app/` services, not in route handlers beyond orchestration.
- Match existing naming, typing, and import style in Python modules.
- Prefer small, focused changes. Update `docs/` when behavior or architecture changes.
- Do not commit secrets (`.env`, API keys) or large binary artifacts (Piper voices, built sidecars).

## Pull requests

1. Fork and create a feature branch from `main`.
2. Test backend changes locally (`/health`, chat flow, Piper if available).
3. For desktop changes, verify `npm run sidecar:build` and `npm run desktop:dev` on your platform.
4. Describe what changed and how you tested it.

## Security

Report vulnerabilities per [SECURITY.md](SECURITY.md). Do not open public issues for unpatched security bugs.

## Releases

Maintainers: after building release assets, run `scripts/generate-sha256.ps1` and attach `SHA256.txt` to the GitHub release. Update VirusTotal links in [docs/TRUST.md](docs/TRUST.md).

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
