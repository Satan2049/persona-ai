# Changelog

All notable changes to this project are documented here.

## [1.3.2] — 2026-07-16

### Added

- **GLB avatars** (Ready Player Me / Wolf3D style) with embedded textures — `ui/avatars/{gender}/avatar.glb`
- Voice sanctuary as the **default first screen** on launch
- FAQ conversational **roadmap** with high priority in the system prompt (ranked by user message)
- GitHub Actions workflows for **Linux** and **macOS** desktop builds

### Changed

- Lip-sync morph mapping for Oculus/RPM visemes (`viseme_aa`, `viseme_E`, …) on GLB models
- Landing page and docs updated for GLB + Rhubarb + OpenAI-compatible TTS/STT (no Piper / no RAG)

### Removed

- Temporary **trial demo** limiter (`TRIAL_MODE`, 3-request cap)
- Legacy VRM sample avatars and external `textures/` folders (textures live inside the GLB)

## [1.3.1] — 2026-07-13

### Fixed

- Installed desktop app showed a blank avatar: VRM now loads from the sidecar HTTP URL after backend ready (Tauri asset protocol fails on large `.vrm` files)
- `Cannot set properties of undefined (setting 'colorSpace')` from three-vrm when a material texture slot is empty

## [1.3.0] — 2026-07-13

### Added

- **Rhubarb Lip Sync** — mouth cues from TTS WAV (`apps/backend/app/rhubarb.py`); shapes A–H / X drive the avatar
- `npm run rhubarb:ensure` downloads Windows binary into `tools/rhubarb/`
- Avatar pipeline (`ui/avatar3d.js`) with male/female models
- WAV header repair for cloud TTS files that ship `0xFFFFFFFF` chunk sizes (GapGPT/OpenAI-compatible)
- Natural idle arm pose (arms down)

### Fixed

- Lip sync producing a single closed mouth cue because broken WAV headers made Rhubarb see `duration: 0`
- Desktop CSP blocking WebGL / WASM (`wasm-unsafe-eval`) so the 3D avatar could stay blank
- Avatar camera framing (head/neck portrait with crown margin)
- `AUDIO_OUTPUT_DIR` resolved to an absolute path under the desktop sidecar

### Removed

- Character-heuristic viseme timeline (text → mouth)
- USC bust packs and related conversion scripts

## [1.2.0] — 2026-07-07

### Added

- **Microphone voice input** — record from the default device, transcribe via OpenAI-compatible STT (`POST /v1/audio/transcriptions`), then send to chat
- New endpoint `POST /chat/transcribe` and `STT_*` env vars (falls back to `TTS_*` / `MODEL_*`)
- Browser Web Speech API fallback when backend STT is not configured
- Mic button (🎤) in the chat input row with recording indicator

## [1.1.0] — 2026-07-07

### Added

- OpenAI-compatible HTTP TTS (`POST /v1/audio/speech`) via `TTS_API_*` env vars (falls back to `MODEL_*`)
- Built-in voice catalog (alloy, shimmer, nova, …) with locale defaults `TTS_VOICE_FA` / `TTS_VOICE_EN`
- Health diagnostics for TTS API key and base URL

### Changed

- **Removed Piper** — no bundled binary, no `piper_models/`, no ONNX voice files
- Desktop bundle no longer ships `resources/piper/` or `resources/piper_models/`
- Setup help and i18n updated for cloud/local OpenAI-compatible TTS

### Removed

- Piper subprocess synthesis, `PIPER_*` environment variables, and [docs/piper-setup.md](docs/piper-setup.md)

## [1.0.0] — 2026-07-05

### Added

- Automatic background sidecar startup in the Tauri desktop app
- Custom frameless title bar with F11 fullscreen
- In-app setup guidance banner (Persian / English) for Ollama and voice models
- Full UI i18n polish for Persian and English

### Changed

- Removed vector RAG; FAQ corpus is now static style context in the system prompt
- Simplified toolbar (theme, language, voice, speed only — no settings panel)
- Windows installer target is **NSIS only** (MSI removed)
- Phone numbers no longer injected into every reply unless the user asks

### Fixed

- Templated replies always mentioning hotline / researcher numbers
