# Persona AI Backend

FastAPI service for the psychologist avatar: OpenAI-compatible **chat**, locale-specific system prompts (Persian / English), **OpenAI-compatible TTS**, **Rhubarb lip-sync**, bundled FAQ style examples, and the bundled **UI** at `http://127.0.0.1:8000/`.

Project overview: **[../../README.md](../../README.md)**.

## Run locally

1. Create a virtual environment in `apps/backend/` and install: `pip install -r requirements.txt`
2. Copy `.env.example` → `.env` and configure `MODEL_*` and optionally `TTS_*`.
3. Install Rhubarb (once): from repo root `npm run rhubarb:ensure`
4. **Start the server**

   From repo root:

   ```text
   scripts\start-backend.bat
   ```

   Or from this folder: **`run.bat`** or:

   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

5. Open **http://127.0.0.1:8000/**

## Production / sidecar entrypoint

For desktop packaging:

```bash
python run_prod.py
```

Environment variables `PERSONA_HOST` and `PERSONA_PORT` control the bind address. Writable data defaults to `%APPDATA%\PersonaAI\` on Windows.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Status, model id, FAQ example count, TTS/STT/Rhubarb configuration |
| `GET` | `/config` | `{ voices, modelName }` for the UI |
| `POST` | `/chat/transcribe` | Multipart audio → transcript (STT) |
| `POST` | `/chat/respond` | Chat + TTS + Rhubarb visemes |
| `GET` | `/audio/{filename}` | Generated WAV under `AUDIO_OUTPUT_DIR` |
| `GET` | `/metrics/summary` | Running latency averages |
