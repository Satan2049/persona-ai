<p align="center">
  <img src="assets/icons/app-icon.svg" width="128" alt="Persona AI logo" />
</p>

<h1 align="center">Persona AI</h1>

<p align="center">
  <strong>Offline-first psychologist avatar</strong> — supportive chat, local Piper TTS, lip-sync, and FAQ-grounded RAG
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT" /></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10--3.12-3776AB?logo=python&logoColor=white" alt="Python 3.10-3.12" /></a>
  <a href="https://tauri.app/"><img src="https://img.shields.io/badge/Tauri-2-24C8DB?logo=tauri&logoColor=white" alt="Tauri 2" /></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href=".github/workflows/backend.yml"><img src="https://img.shields.io/badge/CI-backend-lightgrey" alt="Backend CI" /></a>
</p>

<p align="center">
  <a href="#installation">Installation</a> ·
  <a href="#development">Development</a> ·
  <a href="#build">Build</a> ·
  <a href="docs/TRUST.md">Verify releases</a> ·
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

---

## Description

**Persona AI** is an open-source research demo: a supportive psychologist-style assistant with a **2D avatar**, **lip-sync**, and **local text-to-speech**. A FastAPI backend connects to an OpenAI-compatible LLM, optional FAQ-grounded retrieval (RAG), and [Piper](https://github.com/OHF-Voice/piper1-gpl) for offline speech synthesis. A **Tauri desktop app** packages the same stack for Windows.

> **Disclaimer:** This is a research / demo assistant. It does not diagnose or replace professional mental-health care. Configure emergency and researcher contact numbers in `apps/backend/.env`.

---

## Features

- **Bilingual UI** — Persian and English with locale-locked system prompts
- **Offline TTS** — Piper voices discovered from disk; WAV output with viseme timelines
- **Lip-sync avatar** — mouth animation driven by returned viseme data
- **FAQ-grounded RAG** — retrieval over `data/faq_dataset.json` (on by default)
- **Safety layer** — high-risk content detection and escalation replies
- **Desktop app** — Tauri shell + PyInstaller Python sidecar (Windows installers)
- **Themeable UI** — multiple color themes and voice / face-age controls

---

## Screenshots

<p align="center">
  <img src="assets/screenshots/01-chat.svg" alt="Chat session" width="49%" />
  <img src="assets/screenshots/02-avatar.svg" alt="Avatar and lip-sync" width="49%" />
</p>

<p align="center">
  <img src="assets/screenshots/03-voices.svg" alt="Voice library" width="49%" />
  <img src="assets/screenshots/04-settings.svg" alt="Settings panel" width="49%" />
</p>

<p align="center"><em>UI mockups — replace with real captures in <code>assets/screenshots/</code> when ready.</em></p>

---

## Demo video

**[Watch the demo →](https://github.com/Satan2049/persona-ai/releases/download/v.0.1.0/demo.mp4)** — screen recording of chat, Piper TTS, lip-sync, and the Windows desktop app.

---

## Installation

### Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Python 3.10–3.12** | Recommended; 3.14 may break `pydantic` wheels |
| **Node.js 20+** | Desktop build only |
| **Rust** | Desktop build only |
| **LLM API** | Ollama, vLLM, or any OpenAI-compatible chat endpoint |
| **Embeddings API** | For RAG (defaults to same base as LLM) |
| **Piper** | Binary + voice models — [docs/piper-setup.md](docs/piper-setup.md) |

### Quick start (web / dev server)

```bash
git clone https://github.com/Satan2049/persona-ai.git
cd persona-ai/apps/backend
python -m venv .venv
```

**Windows:** `.venv\Scripts\activate` · **Linux/macOS:** `source .venv/bin/activate`

```bash
pip install -r requirements.txt
cp .env.example .env    # Windows: copy .env.example .env
```

Edit `apps/backend/.env` — set `MODEL_*`, `PIPER_BIN`, and paths. Then from the repo root:

```text
scripts\start-backend.bat        # Windows
./scripts/start-backend.ps1      # PowerShell
```

Open **http://127.0.0.1:8000/** · Health check: **http://127.0.0.1:8000/health**

### Desktop app (release)

Download the latest installer from **[GitHub Releases](https://github.com/Satan2049/persona-ai/releases)**.

Verify downloads with [docs/TRUST.md](docs/TRUST.md) (SHA256 checksums and [VirusTotal](https://www.virustotal.com/) scans).

---

## Development

```text
persona-ai/
├── apps/
│   ├── backend/          # FastAPI, RAG, Piper
│   └── desktop/          # Tauri + sidecar packaging
├── assets/               # Icons, screenshots, config
├── data/                 # FAQ corpus, RAG index
├── docs/                 # Architecture, trust, Piper setup
├── scripts/              # Dev and release helpers
└── ui/                   # Static avatar chat frontend
```

| Task | Command |
|------|---------|
| Start API (dev) | `scripts/start-backend.bat` |
| Backend docs | [apps/backend/README.md](apps/backend/README.md) |
| Desktop docs | [apps/desktop/README.md](apps/desktop/README.md) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Security | [SECURITY.md](SECURITY.md) |

**Not in git:** Piper binary, voice `.onnx` files, API keys, generated `audio/` and `data/rag_index/`.

---

## Build

### Python sidecar (PyInstaller)

```powershell
npm run sidecar:build
# or: .\scripts\build-sidecar.ps1
```

Output: `apps/desktop/src-tauri/binaries/persona-backend-x86_64-pc-windows-msvc.exe`

### Desktop installers (Tauri)

```powershell
npm install
npm run desktop:build
# or: .\scripts\build-desktop.ps1
```

Installers: `apps/desktop/src-tauri/target/release/bundle/`

### Release checksums

Copy release `.exe` / `.zip` / `.msi` files into `dist/release/`, then:

```powershell
.\scripts\generate-sha256.ps1 -ReleaseDir "dist\release"
```

Upload `SHA256.txt` with the release. See [docs/TRUST.md](docs/TRUST.md).

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Frontend | HTML, CSS, vanilla JavaScript (`ui/`) |
| API | [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) |
| RAG | NumPy vector store, OpenAI-compatible embeddings |
| TTS | [Piper](https://github.com/OHF-Voice/piper1-gpl) (subprocess) |
| LLM | OpenAI-compatible HTTP (Ollama, etc.) |
| Desktop shell | [Tauri 2](https://tauri.app/) (Rust) |
| Sidecar | [PyInstaller](https://pyinstaller.org/) |

---

## Documentation

- [docs/rag-system.md](docs/rag-system.md) — RAG design
- [docs/desktop-data-layout.md](docs/desktop-data-layout.md) — install/portable folders, models, Piper voices
- [docs/TRUST.md](docs/TRUST.md) — verify release hashes and VirusTotal
- [docs/architecture/overview.md](docs/architecture/overview.md) — system overview
- [docs/intelligent-avatar-program.md](docs/intelligent-avatar-program.md) — program notes

---

## License

MIT — see [LICENSE](LICENSE).

Third-party components have their own licenses:

- [Piper (piper1-gpl)](https://github.com/OHF-Voice/piper1-gpl) — GPL; review before redistribution
- [piper-voices](https://huggingface.co/rhasspy/piper-voices) — per-voice licenses on Hugging Face
