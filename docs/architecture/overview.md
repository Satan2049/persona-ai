# Architecture overview

Persona AI is a monorepo with three runtime surfaces:

| Surface | Location | Role |
|---------|----------|------|
| Web UI | `ui/` | Avatar chat client (static HTML/JS) |
| Backend | `apps/backend/` | FastAPI API, RAG, Piper TTS orchestration |
| Desktop | `apps/desktop/` | Tauri shell; spawns Python sidecar |

## Request flow

```
Browser / Tauri WebView
        → GET /  (static UI)
        → POST /chat/respond
              → RAG retrieve (optional)
              → LLM (OpenAI-compatible HTTP)
              → Piper subprocess (WAV)
              → viseme timeline
        ← JSON + audio URL
```

## Path resolution

`apps/backend/app/paths.py` resolves locations for:

- **Development** — repo root (`data/`, `piper_models/`, `ui/`)
- **Desktop sidecar** — PyInstaller bundle + `%APPDATA%/PersonaAI/` for writable data

## Desktop bundle

```
Persona AI.exe (Tauri)
    spawns persona-backend sidecar (PyInstaller)
        serves bundled ui/ + API on 127.0.0.1:<ephemeral port>
```

See [apps/desktop/README.md](../../apps/desktop/README.md) for build steps.
