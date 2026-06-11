# Piper TTS setup

Piper turns the assistant’s text reply into **offline WAV audio** for the avatar. This repo does **not** ship the Piper program or voice weights; download them once and point `apps/backend/.env` at them.

## Overview

| Piece | What it is | Where it goes |
|-------|------------|----------------|
| **Piper binary** | `piper.exe` (Windows) plus its DLLs | Any folder; set `PIPER_BIN` to the full path |
| **Voice model** | Two files per voice: `*.onnx` + `*.onnx.json` | `piper_models/` (default `PIPER_MODELS_DIR`) |

## Step 1 — Download the Piper executable

Use **[piper1-gpl](https://github.com/OHF-Voice/piper1-gpl)** (GPL-licensed Piper build):

1. Open **https://github.com/OHF-Voice/piper1-gpl**
2. Download a **release** build for your OS (on Windows, use the amd64 archive that contains `piper.exe`).
3. Extract and keep **`piper.exe` and every `.dll`** in the same folder.

```env
PIPER_BIN=D:\tools\piper\piper.exe
```

**Windows DLL error (0xC0000135):** install [VC++ Redistributable 2015–2022 x64](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).

## Step 2 — Download voice models

Voices: **[rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices)** on Hugging Face.

Place matching `*.onnx` + `*.onnx.json` pairs in `piper_models/`. Examples:

- `en_US-amy-medium.onnx` + `.onnx.json`
- `fa_IR-amir-medium.onnx` + `.onnx.json`

## Step 3 — Verify

1. Start the backend (`scripts/start-backend.bat`).
2. Open **http://127.0.0.1:8000/health** — `tts.piperExecutableOk` should be `true`.
3. Send a chat message and confirm speech + lip movement.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No voices in UI | Both `.onnx` and `.onnx.json` must exist with the same basename |
| `piperExecutableOk: false` | Fix `PIPER_BIN` path |
| ONNX “Missing Input: sid” | Set `PIPER_SPEAKER_ID=0` or `PIPER_ALWAYS_SPEAKER=1` |

See also [piper_models/README.md](../piper_models/README.md).
