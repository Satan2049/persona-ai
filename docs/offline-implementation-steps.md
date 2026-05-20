# Offline Implementation Steps (<= 5M Toman)

## Project Rule
- Fully offline runtime.
- No foreign service dependency.
- Keep implementation minimal, measurable, and thesis-ready.

## Step-by-Step Plan

1. **UI Foundation (Modern + Local)**
   - Build a local, modern interface with:
     - avatar panel,
     - chat history,
     - user input area,
     - voice/lip-sync status indicators.
   - Keep layout responsive and clean.

2. **Local Backend Skeleton**
   - Create local API service (`/health`, `/chat/respond`).
   - Define request/response contract for text + audio + visemes.

3. **Iranian Model Integration**
   - Connect backend to your Iranian model endpoint.
   - Add timeout, retries, and structured error handling.

4. **Offline TTS Integration**
   - Integrate Piper TTS CLI/service.
   - Save output audio locally and return local path.

5. **Lip-Sync Engine**
   - Convert phonemes to viseme timeline.
   - Animate avatar mouth from timeline while audio plays.

6. **Safety Layer**
   - Add psychologist-style policy prompt.
   - Add high-risk message template and escalation guidance.

7. **Evaluation + Demo**
   - Measure latency, sync offset, and user feedback.
   - Prepare thesis report and demo video.

## RAG (FAQ-grounded retrieval)

- **Status:** integrated; starts with the backend (`RAG_ENABLED=true` by default).
- FAQ corpus: `data/faq_dataset.json` (107 curated Persian rows, JSON array only).
- On startup: build/refresh `data/rag_index/` via Ollama (or any OpenAI-compatible embeddings API).
- Details: **`docs/rag-system.md`**

## Current Status
- Step 1: **Completed** (`ui/` modern local prototype created).
- Step 2: **Completed** (`backend/app/main.py` + `ui` wired to `/health` and `/chat/respond`).
- Step 3: **Completed** (Iranian model endpoint integrated with timeout/retry and explicit error handling).
- Step 4: **Completed** (Piper offline TTS integrated; wav saved locally and served from backend).
- Step 5: **Completed** (viseme timeline generated from text + wav duration; UI now animates lips from returned timeline).
- Step 6: **Completed** (high-risk input detection, escalation response, and non-diagnostic safety rewrite added).
- Step 7: **Completed** (evaluation metrics added in backend and thesis demo runbook documented).
