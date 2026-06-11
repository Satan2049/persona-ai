# Desktop & portable data layout

Persona AI **does not ship** LLM weights, Piper voices, or Piper itself. After install or in a portable build, you add those yourself. The app stores **your settings and generated data** under a per-user folder.

## Where things live

| What | Installed desktop app | Dev server (`scripts/start-backend`) |
|------|------------------------|--------------------------------------|
| **Settings (`.env`)** | `%APPDATA%\PersonaAI\.env` | `apps/backend/.env` (fallback) + `%APPDATA%\PersonaAI\.env` if present |
| **Piper voices** | `%APPDATA%\PersonaAI\piper_models\` | `piper_models/` at repo root (or path in `.env`) |
| **Generated audio** | `%APPDATA%\PersonaAI\audio\` | `audio/` or AppData |
| **RAG index** | `%APPDATA%\PersonaAI\rag_index\` | `data/rag_index/` or AppData |
| **FAQ corpus** | Bundled inside sidecar (read-only) | `data/faq_dataset.json` |
| **UI** | Bundled inside sidecar (read-only) | `ui/` |

On Linux/macOS, AppData is `~/.local/share/PersonaAI/` or `~/Library/Application Support/PersonaAI/`.

Configure everything from **Settings** in the app (saved to `%APPDATA%\PersonaAI\.env`).

## LLM models (Ollama, etc.)

Persona AI talks to an **OpenAI-compatible HTTP API**. It does **not** download or store LLM weights.

1. Install [Ollama](https://ollama.com/) (or vLLM, a gateway, etc.) separately.
2. Pull models there, e.g. `ollama pull your-model`.
3. In **Settings → LLM**, set:
   - `MODEL_API_BASE` → `http://127.0.0.1:11434/v1`
   - `MODEL_NAME` → your Ollama model name

Embeddings for RAG use the same pattern (**Settings → RAG**), e.g. `nomic-embed-text` on Ollama.

## Piper TTS

| Piece | You provide | Typical location |
|-------|-------------|------------------|
| **Piper executable** | Download from [piper1-gpl](https://github.com/OHF-Voice/piper1-gpl) | e.g. `D:\tools\piper\piper.exe` → set in **Settings → Piper TTS** |
| **Voice models** | `.onnx` + matching `.onnx.json` from [piper-voices](https://huggingface.co/rhasspy/piper-voices) | `%APPDATA%\PersonaAI\piper_models\` |

Example after install:

```text
%APPDATA%\PersonaAI\
  .env
  piper_models\
    en_US-amy-medium.onnx
    en_US-amy-medium.onnx.json
    fa_IR-amir-medium.onnx
    fa_IR-amir-medium.onnx.json
  audio\
  rag_index\
```

## Installed vs portable

| | **NSIS/MSI installer** | **Portable folder** (release zip / `target/release/`) |
|--|------------------------|--------------------------------------------------------|
| **App binaries** | Program Files + resources | Same folder as `persona-ai-desktop.exe` |
| **Sidecar** | Bundled next to app | `persona-backend.exe` in resources |
| **Your config & voices** | Always `%APPDATA%\PersonaAI\` | Still `%APPDATA%\PersonaAI\` (not beside the exe) |
| **Updates** | Re-run installer | Replace exe folder; AppData kept |

Portable builds are “portable” for the **program**, not for moving user data. Copy `%APPDATA%\PersonaAI\` if you migrate machines.

## What is bundled (read-only)

Inside the PyInstaller sidecar:

- FastAPI backend + Python deps
- `ui/` (chat interface)
- `data/faq_dataset.json`
- Default `voice_avatar_map.json`

Not bundled: Piper, voices, LLM, `.env`, RAG index, audio cache.

## First run checklist

1. Install Ollama (or other LLM) and pull chat + embedding models.
2. Download Piper + at least one English and one Farsi voice pair.
3. Open Persona AI → **Settings** → set LLM, Piper paths, and voice folder.
4. **Save backend settings** → check **Status**.
5. Send a test message (speech + lip-sync).

See also [docs/piper-setup.md](piper-setup.md) and [apps/desktop/README.md](../apps/desktop/README.md).
