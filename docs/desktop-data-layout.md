# Desktop & portable data layout

Persona AI ships primarily as a **Windows NSIS installer**; Linux and macOS bundles are produced by GitHub Actions. LLM and TTS credentials are **not** bundled — configure them in `.env`.

During Windows setup you can choose:

| Install scope | Default folder | Admin required |
|---------------|----------------|----------------|
| **Current user** (recommended) | `%LOCALAPPDATA%\Persona AI\` | No |
| **All users** | `C:\Program Files\Persona AI\` | Yes |

## Where things live (installed app)

| What | Per-user install | All-users (Program Files) |
|------|------------------|---------------------------|
| **App + sidecar** | `%LOCALAPPDATA%\Persona AI\` | `C:\Program Files\Persona AI\` |
| **Settings** | `%APPDATA%\PersonaAI\.env` | same |
| **Generated TTS audio** | `%APPDATA%\PersonaAI\audio\` | same |
| **Logs** | `%APPDATA%\PersonaAI\logs\` | same |

On each new sidecar build, `runtime.env` (snapshot of `apps/backend/.env` at build time) can refresh `%APPDATA%\PersonaAI\.env` when `PERSONA_BUILD_ID` changes.

## LLM, TTS & STT

Persona AI uses OpenAI-compatible HTTP APIs:

- Chat: `MODEL_API_BASE` + `/chat/completions`
- Speech: `TTS_API_BASE` (defaults to `MODEL_API_BASE`) + `/audio/speech`
- Transcription: `STT_API_BASE` (defaults to TTS/MODEL base) + `/audio/transcriptions`

Set `MODEL_*` and optionally `TTS_*` / `STT_*` in `apps/backend/.env` before `npm run sidecar:build`, or edit `%APPDATA%\PersonaAI\.env` after install.

## Dev server

| What | Location |
|------|----------|
| Backend `.env` | `apps/backend/.env` |
| Generated audio | `apps/audio/` or `%APPDATA%\PersonaAI\audio\` (cache, safe to delete) |

## Folders you can delete locally

- `apps/audio/` — regenerated TTS cache only
- `%APPDATA%\PersonaAI\audio\` — same cache in the desktop app

## First run checklist

1. Configure your LLM and TTS provider in `.env` (GapGPT, OpenAI, Ollama + compatible TTS, etc.).
2. Run the installer — choose **current user** unless you need a shared machine install.
3. Launch Persona AI and check `/health` via the in-app status banner.
4. Send a test message.

See also [apps/desktop/README.md](../apps/desktop/README.md).
