# Voice conversation

The desktop and web UI open in **voice mode** first (`#voiceSanctuary`).

## Flow

1. User taps the main mic control → STT (`POST /chat/transcribe`) or browser SpeechRecognition
2. Transcript → `POST /chat/respond` (LLM + TTS + Rhubarb)
3. Assistant audio plays while captions sync and the GLB avatar mouth morphs

## Related files

| File | Role |
|------|------|
| `ui/app.js` | `VoiceSession`, mic capture, bootstrap `voiceSession.open()` |
| `ui/avatar3d.js` | Catalog load, VRM/GLB, idle pose, viseme morphs |
| `apps/backend/app/stt.py` | Speech-to-text |
| `apps/backend/app/tts.py` | Text-to-speech + WAV repair |
| `apps/backend/app/rhubarb.py` | Mouth cues from WAV |
| `apps/backend/app/guidance.py` | FAQ roadmap for reply style |
