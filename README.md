# Persona AI — Smart Psychologist Avatar

An offline-first web demo: a supportive psychologist-style assistant with a **2D avatar**, **lip-sync**, and **local text-to-speech**. The backend uses an OpenAI-compatible LLM, optional FAQ-grounded RAG, and [Piper](https://github.com/OHF-Voice/piper1-gpl) for speech synthesis.

> **Disclaimer:** This is a research / demo assistant. It does not diagnose or replace professional mental-health care. Configure emergency and researcher contact numbers in `backend/.env`.

## Features

- Persian and English UI with locale-locked system prompts
- Piper TTS with multiple voices discovered from disk
- FAQ-grounded retrieval (RAG) over `data/faq_dataset.json`
- High-risk content detection with escalation replies
- Bundled web UI served from the backend at `http://127.0.0.1:8000/`

## Project layout

```
persona-ai/
├── backend/
│   ├── run.bat         # Easiest way to start the server on Windows
│   ├── .env.example    # Copy to .env and fill in
│   └── app/            # FastAPI application
├── ui/                 # Static avatar + chat UI
├── data/               # FAQ dataset; RAG index built at runtime
├── piper_models/       # Put downloaded Piper .onnx voices here (not in git)
├── audio/              # Generated WAV files (not in git)
└── voice_avatar_map.json
```

**Not included in this repository:** Piper executable, Piper ONNX voice files, API keys, or generated audio/index artifacts.

## Prerequisites

- **Windows** (recommended for this project’s `run.bat` workflow) or Linux/macOS
- **Python 3.10+**
- An OpenAI-compatible **chat** API (Ollama, vLLM, a private gateway, etc.)
- For RAG (on by default): an OpenAI-compatible **embeddings** API
- **Piper** binary + voice models (see [Piper TTS setup](#piper-tts-setup))

---

## Quick start

### 1. Clone and install Python dependencies

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

On Linux/macOS use `source .venv/bin/activate` and `cp .env.example .env`.

### 2. Configure the LLM and Piper

Edit **`backend/.env`**:

- Set `MODEL_API_BASE`, `MODEL_API_KEY`, and `MODEL_NAME` for your chat API.
- After installing Piper (next section), set `PIPER_BIN` and confirm `PIPER_MODELS_DIR=../piper_models`.

### 3. Install Piper (binary + voices)

Follow **[Piper TTS setup](#piper-tts-setup)** below. You need at least one **English** and one **Farsi** voice if you use both UI languages.

### 4. Start the server

**Windows (recommended):** double-click or run from a terminal:

```text
backend\run.bat
```

`run.bat` changes to the `backend` folder, activates `.venv` if present, and starts Uvicorn on **http://127.0.0.1:8000/** with reload enabled.

**Manual start** (any OS), from the `backend` folder:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 5. Open the UI

Browse to **http://127.0.0.1:8000/**.

Use **Settings** in the UI to confirm the API base, or check **http://127.0.0.1:8000/health** — `tts.piperExecutableOk` and `tts.voiceCount` should be true / greater than zero when Piper is set up correctly.

More detail: [backend/README.md](backend/README.md) · [docs/rag-system.md](docs/rag-system.md)

---

## Piper TTS setup

Piper turns the assistant’s text reply into **offline WAV audio** for the avatar. This repo does **not** ship the Piper program or voice weights; you download them once and point `backend/.env` at them.

### Overview

| Piece | What it is | Where it goes |
|-------|------------|----------------|
| **Piper binary** | `piper.exe` (Windows) plus its DLLs | Any folder; set `PIPER_BIN` to the full path |
| **Voice model** | Two files per voice: `*.onnx` + `*.onnx.json` | `piper_models/` (default `PIPER_MODELS_DIR`) |

The backend scans `PIPER_MODELS_DIR` for matching pairs and fills the **Voice** dropdown in the UI. Voice ids look like `en_US-amy-medium` or `fa_IR-amir-medium` (derived from the `.onnx` filename without extension).

---

### Step 1 — Download the Piper executable

Use **[piper1-gpl](https://github.com/OHF-Voice/piper1-gpl)** (GPL-licensed Piper build):

1. Open **https://github.com/OHF-Voice/piper1-gpl**
2. Download a **release** build for your OS (on Windows, use the amd64 archive that contains `piper.exe`).
3. Extract the archive to a folder, e.g. `D:\tools\piper\` or `persona-ai\piper\`.
4. Keep **`piper.exe` and every `.dll` from that archive in the same folder.** Piper will not start if DLLs are missing.

Set in **`backend/.env`**:

```env
PIPER_BIN=D:\tools\piper\piper.exe
```

Or, if you extracted under the project:

```env
PIPER_BIN=../piper/piper.exe
```

**Windows DLL error (exit code 3221225781 / 0xC0000135):** the process failed before Piper could run — keep all DLLs beside `piper.exe` and install [VC++ Redistributable 2015–2022 x64](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).

---

### Step 2 — Download voice models from Hugging Face

Voices are published under **[rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices)** on Hugging Face. For each link below, open the page, download the model files, and place them in **`piper_models/`** at the repo root.

#### What to download on each Hugging Face page

Each voice folder contains files such as:

- `*.onnx` — the neural voice model (required)
- `*.onnx.json` — Piper config for that model (required)

Download **both** for the voice you want. The **basename must match** (e.g. `en_US-amy-medium.onnx` and `en_US-amy-medium.onnx.json`). If Hugging Face shows different names, rename so the pair shares the same stem before the extension.

#### English voices (`en_US`)

| Voice | Quality | Hugging Face folder |
|-------|---------|---------------------|
| Amy | medium | https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/amy/medium |
| Joe | medium | https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/joe/medium |
| Ryan | high | https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/ryan/high |
| Sam | medium | https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/sam/medium |

Expected local filenames (examples):

- `en_US-amy-medium.onnx` + `en_US-amy-medium.onnx.json`
- `en_US-joe-medium.onnx` + `en_US-joe-medium.onnx.json`
- `en_US-ryan-high.onnx` + `en_US-ryan-high.onnx.json`
- `en_US-sam-medium.onnx` + `en_US-sam-medium.onnx.json`

#### Farsi / Persian voices (`fa_IR`)

| Voice | Quality | Hugging Face folder |
|-------|---------|---------------------|
| Amir | medium | https://huggingface.co/rhasspy/piper-voices/tree/main/fa/fa_IR/amir/medium |
| Ganji | medium | https://huggingface.co/rhasspy/piper-voices/tree/main/fa/fa_IR/ganji/medium |

Expected local filenames (examples):

- `fa_IR-amir-medium.onnx` + `fa_IR-amir-medium.onnx.json`
- `fa_IR-ganji-medium.onnx` + `fa_IR-ganji-medium.onnx.json`

You do **not** need every voice — one English and one Farsi pair is enough to test both locales. Installing all six gives more choices in the UI voice selector.

#### Target folder layout

After downloads, `piper_models/` should look like:

```text
piper_models/
  en_US-amy-medium.onnx
  en_US-amy-medium.onnx.json
  fa_IR-amir-medium.onnx
  fa_IR-amir-medium.onnx.json
  …
```

Default env (usually no change needed):

```env
PIPER_MODELS_DIR=../piper_models
```

Optional — force a default voice per language in the UI:

```env
PIPER_VOICE_ID_EN=en_US-amy-medium
PIPER_VOICE_ID_FA=fa_IR-amir-medium
```

---

### Step 3 — Verify Piper from the running backend

1. Start the server with **`backend\run.bat`** (or `uvicorn` as above).
2. Open **http://127.0.0.1:8000/health**
3. Confirm:
   - `tts.piperExecutableOk` is `true`
   - `tts.voiceCount` is at least `1` (ideally 2+ if you installed both locales)
4. In the UI, pick **English** or **فارسی**, choose a **Voice**, and send a message — you should hear speech and see lip movement.

---

### Piper troubleshooting

| Problem | What to do |
|---------|------------|
| No voices in UI | Check both `.onnx` and `.onnx.json` exist in `piper_models/` with the same basename |
| `piperExecutableOk: false` | Fix `PIPER_BIN` path; on Windows use full path to `piper.exe` |
| **Missing Input: sid** in logs | Multi-speaker ONNX issue — set `PIPER_SPEAKER_ID=0` or `PIPER_ALWAYS_SPEAKER=1` in `.env` |
| Piper exits immediately on Windows | Keep all DLLs next to `piper.exe`; install VC++ Redistributable x64 |

See also [piper_models/README.md](piper_models/README.md) and [backend/README.md](backend/README.md).

---

## Configuration highlights

| Variable | Purpose |
|----------|---------|
| `MODEL_*` | OpenAI-compatible chat LLM |
| `SOCIAL_EMERGENCY_NUMBER` / `RESEARCHER_NUMBER` | Numbers in prompts and escalation text |
| `PIPER_BIN` / `PIPER_MODELS_DIR` | Local TTS binary and voice folder |
| `RAG_*` / `EMBEDDING_*` | FAQ retrieval (on by default) |
| `VOICE_AVATAR_MAP_PATH` | Avatar age per voice (`voice_avatar_map.json`) |

Copy from [backend/.env.example](backend/.env.example). **Do not commit** `backend/.env`.

## Avatar voice mapping

`voice_avatar_map.json` maps Piper voice ids to avatar face age (`child`, `young`, `old`). The default `"*"` entry applies to all voices; override per voice as needed. Examples: [voice_avatar_map.example.json](voice_avatar_map.example.json).

## Documentation

- [backend/README.md](backend/README.md) — API and backend notes
- [docs/rag-system.md](docs/rag-system.md) — RAG design
- [docs/intelligent-avatar-program.md](docs/intelligent-avatar-program.md) — program overview

## GitHub Pages

The root **[index.html](index.html)** is a static project landing page for GitHub Pages. The live avatar app still requires the local backend.

### Publish at `https://USERNAME.github.io/` (user site)

1. Create or rename the repository to **`USERNAME.github.io`** (replace `USERNAME` with your GitHub username).
2. In **`index.html`**, set `GITHUB_USER` and `GITHUB_REPO` at the bottom of the script (`GITHUB_REPO` should be `USERNAME.github.io`).
3. Push to GitHub. Open **Settings → Pages → Build and deployment**: source **Deploy from a branch**, branch **`main`**, folder **`/ (root)`**.
4. After a minute, visit **https://USERNAME.github.io/**.

### Publish from this repo (`persona-ai`)

1. Leave `GITHUB_REPO = "persona-ai"` in **`index.html`** and set `GITHUB_USER`.
2. Enable Pages on branch **`main`**, folder **`/ (root)`**.
3. Site URL: **https://USERNAME.github.io/persona-ai/**

The **`.nojekyll`** file at the repo root tells GitHub Pages not to run Jekyll, so static assets (including `ui/`) are served as-is.

## License

MIT — see [LICENSE](LICENSE). Piper ([piper1-gpl](https://github.com/OHF-Voice/piper1-gpl)) and [piper-voices](https://huggingface.co/rhasspy/piper-voices) have their own licenses; check those projects before redistribution.
