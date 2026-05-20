# Intelligent Offline Psychologist Avatar Program (Thesis Proposal)

## 1) Goal and Fixed Constraints
- Build an intelligent avatar that guides users in a psychologist-like supportive style.
- Full offline execution (no foreign APIs/services).
- Max target budget: around 5,000,000 toman for thesis implementation.
- Use your Iranian model as the only AI backend.

---

## 2) Offline-Only Architecture

### A. Frontend (Local UI)
- Web UI (HTML/CSS/JS or React, local).
- Avatar scene (2D first to reduce cost and complexity).
- Audio player and lip-sync timeline runner.
- Local connection to backend (`localhost` / local network only).

### B. Backend (Local Service)
- FastAPI (Python) or Fastify (Node.js), running on local machine.
- Responsibilities:
  1. Session state management.
  2. Safety prompt injection for guidance behavior.
  3. Call Iranian model API (local/private).
  4. Generate speech with offline TTS.
  5. Create viseme timeline for avatar lip movement.

### C. AI and Voice Layer (Offline)
- LLM: Iranian model endpoint in local/private environment.
- TTS: Piper TTS (preferred for low resource and zero API cost).
- Optional STT: Vosk (only if microphone input is needed).

### D. Storage Layer
- SQLite for conversation/session metadata.
- Local file storage for generated `.wav` audio and cached visemes.

---

## 3) Core Runtime Pipeline
1. User sends text (or optional voice converted locally to text).
2. Backend applies safe psychologist-style system prompt.
3. Backend queries Iranian model.
4. Backend converts answer to speech with local TTS.
5. Backend runs phoneme-to-viseme mapping.
6. Backend returns:
   - assistant text,
   - local audio path,
   - viseme timeline.
7. Frontend plays audio and animates lips using timeline.

---

## 4) Lip Sync in Low-Budget Mode

### Primary Implementation (MVP)
- Rule-based phoneme approximation for Persian text.
- Map phoneme groups to 4-6 visemes for stable animation.
- Use smoothing (attack/release) to reduce mouth jitter.

### Optional Improvement
- Add offline forced alignment later for better timing.

---

## 5) Safety and Psychology Policy
- Supportive, empathetic, non-diagnostic responses.
- No medical claims or psychiatric diagnosis.
- Risk-aware response template for self-harm/high-risk content.
- Recommend professional help when needed.

---

## 6) Budget Plan (<= 5M Toman)
- Software stack: open source and free.
- Infra: local machine, no cloud dependency.
- Expected direct cost: near-zero to low.
- Main cost is development time.
- Keep scope to MVP + measurable thesis evaluation.

---

## 7) Suggested Minimal Tech Stack
- Backend: Python + FastAPI
- Frontend: local web app (start with vanilla UI, optional React later)
- TTS: Piper
- Database: SQLite
- Avatar: 2D canvas-based face rig (first release)

---

## 8) Execution Milestones
1. Build modern local UI shell and avatar stage.
2. Connect UI to local backend endpoint.
3. Integrate Iranian model response pipeline.
4. Integrate offline TTS and local audio playback.
5. Add viseme timeline and lip movement sync.
6. Add safety prompts and risk handling.
7. Run thesis metrics and prepare demo.

---

## 9) Success Metrics (Thesis)
- Response latency (ms).
- Audio generation time (ms).
- Lip-sync offset (ms).
- User-rated naturalness of avatar movement.
- User-rated empathy/helpfulness score.

---

## 10) Deliverables
- Offline runnable source code (frontend + backend).
- Configuration guide for local machine setup.
- Evaluation report with metrics and constraints.
- Demo video showing Iranian model + offline voice + lip sync.

