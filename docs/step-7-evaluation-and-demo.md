# Step 7 - Evaluation and Demo Runbook

## Goal
Produce thesis-grade evidence for:
- latency,
- lip-sync quality,
- safety behavior,
- user-perceived helpfulness.

## A) Metrics to Collect

### 1) Backend Performance Metrics
Use response metadata in `POST /chat/respond`:
- `meta.latencyMs.model`
- `meta.latencyMs.tts`
- `meta.latencyMs.total`
- `meta.durationMs`
- `meta.safety.isHighRiskInput`

Use aggregate endpoint:
- `GET /metrics/summary`

Record at least 30 interactions across normal and stress scenarios.

### 2) Lip-Sync Metrics
For each test response:
- Compare audio start and first visible mouth movement.
- Measure sync offset in ms.
- Target: average offset under 200 ms for thesis MVP.

### 3) Safety Metrics
Prepare 10 high-risk prompts and 20 normal prompts.
Check:
- high-risk prompts must trigger escalation-safe behavior,
- model must avoid direct diagnosis language.

### 4) User Study Metrics (Lightweight)
At least 8-15 participants, each with 5-10 minute session.
Rate 1-5:
- perceived empathy,
- clarity of guidance,
- voice naturalness,
- avatar realism,
- overall trust.

## B) Scenario Test Set
1. Normal stress question.
2. Academic anxiety question.
3. Sleep-related stress question.
4. Repeated short prompts (load behavior).
5. High-risk self-harm statement.
6. Ambiguous emotional distress statement.

## C) Demo Day Checklist
- Backend runs locally and `/health` is OK.
- Iranian model endpoint reachable.
- Piper model path configured and audio generation works.
- `/chat/respond` returns text + audio path + visemes.
- UI plays audio and lips move in sync.
- Safety response shown correctly on high-risk sample.
- Collect screenshots/video from successful runs.

## D) Report Tables (for thesis)
Prepare 4 tables:
1. Latency table (model, tts, total).
2. Lip-sync offset table.
3. Safety pass/fail table for scenario set.
4. User feedback summary table (mean and std for each score).

## E) Minimum Acceptance Criteria
- End-to-end offline operation.
- Average total latency in acceptable thesis range (report measured value).
- Lip-sync visibly synchronized in demo video.
- High-risk prompts handled with escalation-safe output.
