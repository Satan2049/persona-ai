# Architecture overview

| Layer | Path | Role |
|-------|------|------|
| Backend | `apps/backend/` | FastAPI API, OpenAI-compatible LLM/TTS/STT, Rhubarb lip sync |
| UI | `ui/` | Vanilla JS chat + voice sanctuary + Three.js GLB avatar |
| Desktop | `apps/desktop/` | Tauri shell + PyInstaller sidecar |

## Chat + speech path

```
Client POST /chat/respond
  → FAQ roadmap injected into system prompt (high priority)
  → LLM (OpenAI-compatible)
  → TTS HTTP /audio/speech → WAV
  → Rhubarb Lip Sync → mouth cues A–H / X
  → JSON { assistantText, audioPath, visemes, meta.lipSync }
  → UI plays audio + drives GLB morph targets / visemes
```

## FAQ guidance

`data/faq_dataset.json` is not RAG. It is a **conversational roadmap**: short clarifying questions grouped by category. Closest rows to the user message are ranked first and placed ahead of the base system prompt.

## Lip sync

Visemes come from **audio analysis** (Rhubarb), not from guessing letters in the reply text.

- Install (Windows): `npm run rhubarb:ensure` → `tools/rhubarb/rhubarb.exe`
- Persian / non-English: `-r phonetic`
- English: `-r pocketSphinx` (+ dialog text when available)

## Avatars

Only **GLB** is loaded (`ui/avatars/{gender}/avatar.glb`). Source files live under `assets/avatars/{gender}/source/`. Textures are embedded in the GLB.

## Voice-first UI

On launch the app opens the **voice sanctuary** (full-screen conversation). Users can switch to chat from there.

## Desktop packaging

| Platform | Sidecar | Installer |
|----------|---------|-----------|
| Windows | `persona-backend-<triple>.exe` | NSIS |
| Linux | `persona-backend-<triple>` | AppImage / deb (CI) |
| macOS | `persona-backend-<triple>` | DMG (CI) |
