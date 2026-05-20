# RAG System — Smart Avatar (FAQ-Grounded Guidance)

## 1) Goal and Fixed Constraints

- Ground the psychologist-style assistant on **`data/faq_dataset.json`** so replies stay aligned with curated empathy, reflection, and Socratic questions.
- Keep the existing **safety layer** (high-risk detection, escalation, non-diagnostic policy) and **short reply** rules from the chat model.
- **Retrieval augments** the LLM; it does not replace the model or copy FAQ text verbatim unless similarity is very high.
- **Embedding API**: you supply `EMBEDDING_API_KEY` and endpoint; the repo ships structure, index build script, and integration hooks only.
- Runtime: local FastAPI backend; index files live under `data/rag_index/`.
- **Startup**: when the backend starts, it builds or refreshes the index if needed and preloads vectors (see §7).

---

## 2) Knowledge Source (`faq_dataset.json`)

### Canonical record shape (use this everywhere)

Each FAQ item is one object:

```json
{
  "user": "نمی‌تونم قبل از عمل کردن فکر کنم",
  "responses": [
    "بیاییم چند ثانیه بین احساس و عمل فاصله بسازیم.",
    "می‌فهمم چقدر سخته، بیا قدم‌به‌قدم پیش بریم.",
    "آیا همیشه هیچ فرصتی برای مکث نداشتی؟"
  ],
  "category": "impulsivity"
}
```

| Field | Role |
|--------|------|
| `user` | Typical user utterance (retrieval query is matched against this text). |
| `responses` | 1–3 example assistant lines (style and content hints for the generator). |
| `category` | Theme tag for filtering and logging (`impulsivity`, `distress`, `relationship`, `emotion`, `identity`, …). |

### Categories in the current seed set

- `impulsivity` — acting before thinking, regret, loss of control  
- `distress` — exhaustion, hopelessness (still routed through safety rules)  
- `relationship` — loneliness, fear of being alone  
- `emotion` — anger, mood swings  
- `identity` — confusion about self  

### File hygiene

- Keep **`data/faq_dataset.json` as one valid JSON array** only (no `جمله فرد:` / `آواتار:` prose after `]`).
- To convert legacy prose, run once: `python scripts/convert_faq_prose.py` from `backend/`.
- Each `user` string should appear once; duplicates are merged by normalized text.

---

## 3) RAG Architecture (offline index, online retrieve)

```
┌─────────────────┐     build (CLI)      ┌──────────────────────┐
│ faq_dataset.json│ ──────────────────► │ data/rag_index/      │
└─────────────────┘   embed + save       │  meta.jsonl          │
                                         │  vectors.npy         │
                                         └──────────┬───────────┘
                                                    │
User message ──► embed query ──► top-k cosine ──► context block ──► LLM (+ system prompt)
```

| Component | Path | Responsibility |
|-----------|------|------------------|
| Loader | `backend/app/rag/loader.py` | Parse FAQ JSON array only. |
| Chunking | `backend/app/rag/chunking.py` | One searchable document per FAQ row. |
| Embeddings | `backend/app/rag/embeddings.py` | HTTP client to your embedding API. |
| Store | `backend/app/rag/store.py` | Persist vectors + metadata on disk. |
| Retriever | `backend/app/rag/retriever.py` | Top-k similarity search. |
| Composer | `backend/app/rag/composer.py` | Format retrieved rows for the LLM. |
| Service | `backend/app/rag/service.py` | `retrieve(user_text, locale)` entry point. |
| Bootstrap | `backend/app/rag/bootstrap.py` | Build index on startup, preload vectors. |
| Build script | `backend/scripts/build_rag_index.py` | Manual index rebuild (same logic as bootstrap). |

---

## 4) Index Document Format (what gets embedded)

For each FAQ record we build **one chunk** (no sentence splitting in v1):

**Embedding text** (Persian-heavy; normalize whitespace):

```
user: {user}
category: {category}
```

**Stored metadata** (not embedded, returned on hit):

- `id` — stable index `faq-{n}`  
- `user`, `category`  
- `responses` — full list for the prompt composer  

Optional later: embed `user + " " + responses[0]` for richer recall; v1 keeps queries aligned with real user phrasing.

---

## 5) Embedding Configuration (you fill in secrets)

Add to `backend/.env` (see `backend/.env.example`):

| Variable | Purpose |
|----------|---------|
| `RAG_ENABLED` | `true` (default) injects retrieval into `/chat/respond`. |
| `RAG_BUILD_ON_STARTUP` | `true` (default) rebuild index when FAQ is newer than `meta.jsonl`. |
| `RAG_FAQ_PATH` | Path to `faq_dataset.json`. |
| `RAG_INDEX_DIR` | Output folder for `vectors.npy` + `meta.jsonl`. |
| `EMBEDDING_API_BASE` | OpenAI-compatible base URL; defaults to `MODEL_API_BASE` (Ollama: `http://127.0.0.1:11434/v1`). |
| `EMBEDDING_API_KEY` | API key; defaults to `MODEL_API_KEY` (`local-key` for Ollama). |
| `EMBEDDING_MODEL` | Model id (Ollama example: `nomic-embed-text`). |
| `EMBEDDING_TIMEOUT_SECONDS` | HTTP timeout. |
| `RAG_TOP_K` | Number of FAQ rows passed to the LLM (default `4`). |
| `RAG_MIN_SCORE` | Minimum cosine similarity `0–1` (default `0.35`). |

The client posts to `{EMBEDDING_API_BASE}/embeddings` with `{"model", "input"}` and reads `data[].embedding`.

**Local Ollama:** `ollama pull nomic-embed-text`, then start the backend; the index is created under `data/rag_index/` automatically.

---

## 6) Runtime Pipeline (chat with RAG)

1. User sends text on `/chat/respond` (unchanged contract).  
2. **Safety** — high-risk check runs first; if triggered, skip RAG and return escalation (unchanged).  
3. **Retrieve** — embed `userText`, load index, cosine top-k, filter by `RAG_MIN_SCORE`.  
4. **Compose context** — append a block to the system message:

   ```
   --- Retrieved guidance (style reference; do not diagnose) ---
   [1] category=impulsivity
   User said: ...
   Example responses: ...
   ---
   ```

5. **Generate** — call the Iranian / local chat model with augmented system prompt + user message.  
6. **TTS + visemes** — unchanged.  
7. **Meta** — add `meta.rag`: `{ enabled, hitCount, categories, scores }` for evaluation.

The model must still follow `SYSTEM_PROMPT_FA` / `SYSTEM_PROMPT_EN`: empathy, brevity, no diagnosis, Persian/English locale rules.

---

## 7) Index build (automatic on startup)

When you run the backend (`uvicorn` or `run.bat`), the lifespan hook calls `initialize_rag()`:

1. If `RAG_ENABLED` and embeddings are configured, load FAQ record count.  
2. If the index is missing or `faq_dataset.json` is newer than `meta.jsonl`, embed all rows and write `data/rag_index/`.  
3. Preload `vectors.npy` + `meta.jsonl` into memory for fast `/chat/respond`.

Check status: `GET /health` (`rag` object) or `GET /rag/status`.

**Manual rebuild** (same as startup) from `backend/`:

```bash
pip install -r requirements.txt
python scripts/build_rag_index.py
```

Rebuild whenever you edit `faq_dataset.json` and want to force an immediate index refresh without restarting (or restart the backend with `RAG_BUILD_ON_STARTUP=true`).

---

## 8) Integration Checklist (backend)

- [x] RAG package under `backend/app/rag/`  
- [x] `build_rag_index.py` script  
- [x] `RAG_ENABLED` wired in `chat_respond` (augments system prompt before `_call_llm`)  
- [x] FastAPI **lifespan** builds/refreshes index and preloads on startup  
- [x] `GET /rag/status` (index ready, FAQ count, embedding configured)  
- [x] `GET /health` includes `rag` startup summary  
- [x] `meta.rag` on chat responses (hits, scores, latency)  

---

## 9) Evaluation (thesis-friendly)

| Metric | How |
|--------|-----|
| Retrieval hit rate | % of user turns with ≥1 chunk above `RAG_MIN_SCORE` |
| Category match | Manual review: retrieved `category` vs expected theme |
| Style adherence | Rubric: empathy, question, no diagnosis (same as non-RAG) |
| Latency | `meta.latencyMs.rag` embed + search ms |
| Regression | Compare answers with `RAG_ENABLED=false` on fixed test prompts |

Suggested test prompts (Persian): reuse `user` strings from the FAQ plus paraphrases not in the file.

---

## 10) Expanding the FAQ (avoid repetition)

1. Add a **new JSON object** inside the array; do not duplicate under `]`.  
2. Keep `responses` to 2–3 short lines (mirror existing tone).  
3. Pick one `category` per row.  
4. Run `build_rag_index.py` again.  
5. Spot-check retrieval with `python -c "..."` or a small `scripts/query_rag.py` (optional).

Legacy `جمله فرد:` / `آواتار:` prose: run `backend/scripts/convert_faq_prose.py` once, then commit the resulting JSON-only file.

---

## 11) Deliverables

| Artifact | Location |
|----------|----------|
| This program | `docs/rag-system.md` |
| FAQ data | `data/faq_dataset.json` |
| RAG code | `backend/app/rag/` |
| Index builder | `backend/scripts/build_rag_index.py` |
| Env template | `backend/.env.example` |

---

## 12) Relation to Other Docs

- **UI / TTS / avatar**: unchanged; see `docs/offline-implementation-steps.md`.  
- **Thesis scope & safety**: `docs/intelligent-avatar-program.md` §5–6.  
- **Demo metrics**: `docs/step-7-evaluation-and-demo.md` — add RAG rows to your evaluation table.

No separate RAG architecture is duplicated there; link to this document when citing retrieval design.
