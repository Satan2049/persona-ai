# Persona AI Backend

FastAPI service for the psychologist avatar: OpenAI-compatible **chat**, locale-specific system prompts (Persian / English), **Piper TTS**, lip-sync visemes, optional **RAG**, and the bundled **UI** at `http://127.0.0.1:8000/`.

Project overview: **[../../README.md](../../README.md)**.

## Run locally

1. Create a virtual environment in `apps/backend/` and install: `pip install -r requirements.txt`
2. Copy `.env.example` → `.env` and configure the LLM, Piper paths, and optional RAG embedding API.
3. Install Piper and voices — [../../README.md#piper-tts-setup](../../README.md#piper-tts-setup).
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
| `GET` | `/health` | Status, model id, RAG summary, Piper / voice discovery |
| `GET` | `/rag/status` | FAQ count, index ready, embedding config |
| `GET` | `/config` | `{ voices, modelName }` for the UI |
| `POST` | `/chat/respond` | Chat + TTS + visemes |
| `GET` | `/audio/{filename}` | Generated WAV under `AUDIO_OUTPUT_DIR` |
| `GET` | `/metrics/summary` | Running latency averages |
