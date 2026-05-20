# Smart Avatar Backend

FastAPI service for the **Persona AI** psychologist avatar: OpenAI-compatible **chat**, locale-specific system prompts (Persian / English), **Piper TTS**, lip-sync visemes, optional **RAG**, and the bundled **UI** at `http://127.0.0.1:8000/`.

Project overview and Piper installation: **[../README.md](../README.md)**.

## Run locally

1. Create a virtual environment in `backend/` and install: `pip install -r requirements.txt`
2. Copy `.env.example` → `.env` and configure the LLM, Piper paths, and optional RAG embedding API.
3. Install Piper and voices — [../README.md#piper-tts-setup](../README.md#piper-tts-setup) ([piper1-gpl](https://github.com/OHF-Voice/piper1-gpl) + [Hugging Face voices](https://huggingface.co/rhasspy/piper-voices)).
4. **Start the server**

   **Windows:** run **`run.bat`** in this folder (double-click or `backend\run.bat` from the repo root). It activates `.venv` if present and starts Uvicorn on port 8000 with reload.

   **Manual:**

   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

5. Open **http://127.0.0.1:8000/**

Check RAG: `GET /rag/status` or `GET /health` (`rag` field).

## Current behavior

- **Chat** (`POST /chat/respond`): LLM with Persian or English system prompt; short replies via prompt + `MODEL_MAX_TOKENS`; trims incomplete sentences; optional RAG context from `data/faq_dataset.json`.
- **Voices**: Scans `PIPER_MODELS_DIR` for `*.onnx` + `*.onnx.json`; UI sends `voiceId` + `locale` (must match).
- **Safety**: High-risk terms trigger fixed escalation text with configurable emergency numbers.
- **Metrics**: `GET /metrics/summary` for latency averages.

## Piper troubleshooting

### Windows exit code 3221225781 (0xC0000135)

DLL failed to load. Keep `piper.exe` and all `.dll` from the release zip in one folder; set `PIPER_BIN` to that executable; install VC++ Redistributable x64. See [../README.md#piper-tts-setup](../README.md#piper-tts-setup).

### ONNX “Missing Input: sid”

Multi-speaker models need `--speaker`. The backend passes it when `num_speakers > 1` in the voice `.json`. Otherwise set `PIPER_SPEAKER_ID=0` or `PIPER_ALWAYS_SPEAKER=1` in `.env`.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Status, model id, RAG summary, Piper / voice discovery |
| `GET` | `/rag/status` | FAQ count, index ready, embedding config |
| `GET` | `/config` | `{ voices, modelName }` for the UI |
| `POST` | `/chat/respond` | Chat + TTS + visemes |
| `GET` | `/audio/{filename}` | Generated WAV under `AUDIO_OUTPUT_DIR` |
| `GET` | `/metrics/summary` | Running latency averages |

## UI without this server

Serve `ui/` over HTTP and set the API base in Settings, or use `?api=http://127.0.0.1:8000`.
