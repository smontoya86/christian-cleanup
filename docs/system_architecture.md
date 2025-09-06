# System Architecture (Master, Router-only)

## Purpose & Capabilities
- What it is: Christian music analysis platform (Flask API + services) that evaluates songs/playlist content using an OpenAI-compatible router (Runpod vLLM preferred; Ollama fallback).
- What it does: Fetches lyrics, analyzes content (score, concern level, themes, scripture), stores results, exposes API for UI and batch flows, and includes an eval harness.

## Overview
- Flask app with blueprints: `auth`, `main`, `api`
- Services: Spotify integration, analysis orchestration, scripture mapping, concern detection
- Data: PostgreSQL via SQLAlchemy 2.0; Redis for cache/sessions
- Deployment: Docker + Compose on port 5001; monitoring ready
- Analysis: Router-only (OpenAI-compatible HTTP) via `RouterAnalyzer`
- Frontend consolidation: `static/js/main.js` + `modules/playlist-analysis.js`; legacy `song-analyzer.js` removed
- In-page progress UI and toasts for playlist analysis
- Admin-only "Analyze All Songs"; hidden from non-admin users
- Cached dashboard stats via `/api/dashboard/stats` (Redis 60s) and server-side pagination
- Data model: `Playlist (owner_id, spotify_id)` unique; `Song.last_analysis_result_id`; `Playlist.has_flagged`
- Admin utilities: `/api/admin/recompute-has-flagged`, `/api/admin/prune-analyses`

## Tech Stack
- Backend: Flask (Gunicorn), Python 3.13
- DB: PostgreSQL (SQLAlchemy 2.x)
- Cache/Queue: Redis (in-memory cache; queues removed)
- HTTP Client: requests (LLM router, providers)
- Containerization: Docker + docker-compose (dev/prod profiles)
- Monitoring: Prometheus/Grafana (optional in prod compose)

## Frontend Architecture
- Rendering: Server-rendered Flask templates in `app/templates` with Bootstrap-based styles in `app/static/css`
- Behavior: Progressive enhancement via JS modules in `app/static/js` (e.g., `main.js` bootstrapping `modules/playlist-analysis.js` for playlist analysis UX)
- UX Flows:
  - Playlist Detail: Analyze/Re-analyze button triggers POST to `main.analyze_playlist`; progress polled via `/api/playlists/<id>/analysis-status`
  - Song Detail: Status and last analysis surfaced via API formatting utilities
- Assets: Static served from `app/static/` (css/js/images); cache-safe filenames under `dist/` when built
- Security: CSRF disabled only in tests; production uses standard Flask protections and Nginx TLS termination

## Model Selection & Router Framework
- Router Analyzer: OpenAI-compatible HTTP client that calls the configured endpoint and normalizes strict JSON.
- Detection order (in-Docker):
  1) `LLM_API_BASE_URL` (if set; default `http://llm:8000/v1` in prod env template)
  2) `http://llm:8000/v1` (Runpod vLLM service in compose)
  3) `http://ollama:11434/v1` (in-docker Ollama fallback)
  4) `http://host.docker.internal:11434/v1` (host fallback for dev)

### Analyzer Profiles
- Local (Ollama):
  - `LLM_API_BASE_URL=http://ollama:11434/v1` (in-docker) or `http://host.docker.internal:11434/v1` (dev host)
  - `LLM_MODEL=llama3.1:8b`
- Runpod (vLLM):
  - `LLM_API_BASE_URL=http(s)://<runpod-host>:<port>/v1`
  - `LLM_MODEL=<llama-3.1-70b-instruct-awq>`
- Tunables:
  - `LLM_TEMPERATURE` (0.2), `LLM_TOP_P` (0.9), `LLM_MAX_TOKENS` (512), `LLM_TIMEOUT` (120–600), `LLM_CONCURRENCY` (1)

### Environment Keys
- Required: `LLM_API_BASE_URL`, `LLM_MODEL`
- Optional: `LLM_TEMPERATURE`, `LLM_TOP_P`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT`, `LLM_CONCURRENCY`, `DISABLE_ANALYZER_PREFLIGHT`
- Detection is implemented in `app/services/analyzer_cache.py` and `app/services/analyzers/router_analyzer.py`.

### Model Profiles (Quick Reference)

| Profile | Endpoint | Example Model | Notes |
|---|---|---|---|
| Runpod (preferred) | `http://llm:8000/v1` or external Runpod URL | `llama-3.1-70b-instruct-awq` | Highest quality/throughput via vLLM. Set `LLM_API_BASE_URL` explicitly in prod. |
| Ollama (fallback) | `http://ollama:11434/v1` | `llama3.1:8b` | In-docker CPU/GPU fallback; slower but always on. |
| Host (dev fallback) | `http://host.docker.internal:11434/v1` | `llama3.1:8b` | Mac/Windows Docker Desktop only; not used in prod. |

## Quick Reference (One-Stop)
- Ports: UI→Nginx 443/80 (prod optional), API `:5001` (external) → Gunicorn `:5000` (internal)
- Services (compose): `web` (Flask), `db` (Postgres), `redis`, `llm` (vLLM), `ollama` (fallback), `nginx` (prod)
- Primary env: `LLM_API_BASE_URL`, `LLM_MODEL`, `DATABASE_URL` or `POSTGRES_*`, `REDIS_URL`, `DISABLE_ANALYZER_PREFLIGHT`
- Detection order: Runpod vLLM → Ollama → host fallback (see above)
- Health: `/api/health`, `/api/health/ready`, `/api/health/live`, admin: `/api/admin/diagnostics`, `/api/admin/warm`
- Analysis entrypoints (API):
  - Single: `POST /api/songs/<id>/analyze` → persists latest `AnalysisResult`
  - Playlist: `POST /api/playlists/<id>/analyze-unanalyzed`
  - Status: `/api/songs/<id>/analysis-status`, `/api/playlists/<id>/analysis-status`, `/api/analysis/status`
- Eval: `python -m scripts.eval.run_eval --input ... --out ...` (router-only). Artifacts under `scripts/eval/reports/reviews/<ts>/`.
- Rollback: see `docs/ROLLBACK_PLAN.md` (git-based; no DB migration reversal required)

## Core Flow
1. UI requests analysis via `/api/...`
2. `UnifiedAnalysisService` delegates to `SimplifiedChristianAnalysisService`
3. `SimplifiedChristianAnalysisService` resolves analyzer via provider (Router by default)
4. Router returns strict JSON → mapped into `AnalysisResult`
5. `EnhancedConcernDetector` and `EnhancedScriptureMapper` enrich results
6. Results persisted to DB and surfaced to UI

## System Architecture
- Nginx (optional in prod) fronts `web` (Flask/Gunicorn) on port 5001.
- `web` communicates with Postgres and Redis over the internal network.
- `web` calls the LLM router endpoint (Runpod vLLM at `llm:8000/v1` by default, falls back to `ollama:11434/v1`).
- Admin endpoints provide diagnostics, preflight, and optional warmup ping (`/admin/warm`).

```mermaid
graph LR
  A[Browser/UI] -->|HTTPS| N[Nginx (prod optional)]
  A -.dev-> W
  N -->|HTTP :5001| W[Flask/Gunicorn (web)]
  W <-->|SQL| P[(PostgreSQL)]
  W <-->|Cache| R[(Redis)]
  subgraph LLM Router
    V[vLLM service llm:8000/v1]
    O[Ollama ollama:11434/v1]
  end
  W -->|OpenAI-compatible /v1| V
  W -.fallback.-> O
  W -.dev fallback.-> H[host.docker.internal:11434/v1]
```

## Expectations (Ops & Product)
- Analyzer: Always prefer Runpod vLLM; auto-fallback to Ollama; never call HF transformers.
- CI: Offline; all router calls mocked; set `DISABLE_ANALYZER_PREFLIGHT=1`, `CI=1`.
- Performance (defaults; tune per model): request timeout 120–600s; concurrency 1; final score 0–100; themes/scripture present when possible.
- Reliability: health endpoints return 200 when DB and cache OK; analyzer preflight not required for app to boot.
- Security: secrets via env; DB and Redis on internal networks; Nginx terminates TLS in prod.

## Testing & Eval
- Unit/integration tests in `tests/` (CI-safe and green by default)
- API E2E smoke: `tests/integration/api/test_api_e2e_smoke.py` exercises `/api/health`, single-song analyze, playlist analyze status with the router mocked
- Frontend tests: Flask test client + BeautifulSoup validate template DOM, button presence/labels, JS includes, and route behavior (see `tests/frontend/test_analyze_playlist_button.py`).
- Eval harness (router-only) computes verdict metrics, MAE, scripture Jaccard; use 2-item smoke before large runs.

### Automated test commands
- Local full suite: `make test` (runs `scripts/test_all.sh`)
- Local smoke: `make test-smoke` (router + API E2E + critical services)
- Docker full: `make test-docker`
- Docker smoke: `make test-smoke-docker`
- npm equivalents: `npm run test`, `npm run test:smoke`

### CI notes
- Set `CI=1` and `DISABLE_ANALYZER_PREFLIGHT=1` to keep runs offline and deterministic; router HTTP is mocked
- Optional: `LYRICS_DISABLE_NEGATIVE_CACHE=1` can be used in highly concurrent CI jobs to avoid negative-cache cross-thread interference during lyrics tests (not needed for default runs)

## Quick Commands (Ops)
- Dev up: `docker compose up -d`
- Prod up: `docker compose -f docker-compose.prod.yml up -d`
- Web logs: `docker compose logs -f web`
- Health: `curl -s localhost:5001/api/health | jq`
- Admin warm: `curl -s -X POST localhost:5001/api/admin/warm | jq`
- Eval smoke: `docker compose exec web python -m scripts.eval.run_eval --input scripts/eval/smoke2.jsonl --out scripts/eval/reports/reviews/$(date +%Y%m%d-%H%M%S)`
- Tests (quick): `make test-smoke` | Full: `make test` | Docker: `make test-docker`

## Troubleshooting (Fast)
- LLM 503/timeout: verify `LLM_API_BASE_URL`, `LLM_MODEL`; check `llm`/`ollama` containers; run `/api/admin/diagnostics`.
- Slow first request: run `/api/admin/warm` (preflight + tiny chat) or increase `LLM_TIMEOUT`.
- CI failures on network: ensure `DISABLE_ANALYZER_PREFLIGHT=1`, router endpoints are mocked by tests.
- No scriptures in results: Router may omit; mapper backfill occurs if themes detected.
- DB connection errors: verify `DATABASE_URL` or `POSTGRES_*` env and service health.

## Performance Targets (Guidance)
- Single analysis p50: < 5s on vLLM (Runpod); p90 < 10s; Ollama fallback slower.
- API health endpoints: < 200ms.
- Eval smoke (2 items): < 20s end-to-end on local dev.

## Key Modules
- `app/services/`
  - `unified_analysis_service.py`: Orchestrates and persists results
  - `simplified_christian_analysis_service.py`: Core orchestration + mapping
  - `provider_resolver.py`: Returns Router analyzer
  - `analyzer_cache.py`: Router-backed cache (legacy interface preserved)
  - `enhanced_scripture_mapper.py`, `enhanced_concern_detector.py`
- `app/services/analyzers/router_analyzer.py`: OpenAI-compatible HTTP client
- `app/models/models.py`: SQLAlchemy models
- `app/utils/`: health, retry, lyrics fetching
- `app/templates/`: Jinja templates for server-rendered views
- `app/static/js/`: Frontend behavior modules (e.g., `main.js`, `modules/playlist-analysis.js`)

## Data Model (essentials)
- `Song(id, title, artist, album, lyrics, ...)`
- `AnalysisResult(song_id, status, score, concern_level, themes, supporting_scripture, created_at, ...)`
- `Playlist`, `PlaylistSong`, `Whitelist`

## Eval Harness (Router-only)
- Entry: `scripts/eval/run_eval.py`
- Usage:
  ```bash
  docker compose exec web python -m scripts.eval.run_eval \
    --input scripts/eval/smoke2.jsonl \
    --out scripts/eval/reports/reviews/$(date +%Y%m%d-%H%M%S)
  ```
- Environment: set analyzer profile variables above
- Outputs: `summary.json`, `predictions.jsonl/csv`, `gpt_review_inputs.*`, `report.html`

## Reliability & Observability
- Correlation ID, structured logs, Prometheus metrics
- Health endpoints and admin diagnostics
- Retry/backoff around external calls (lyrics, LLM)

## Notes (Consolidation)
- HF Transformers/torch pipelines removed from application path
- `analyzer_cache` now returns Router analyzer for legacy interfaces
- Queue/worker paths removed; analysis runs in-process

## Assumptions & Guardrails
- Router-only; no HF pipelines in app path
- All services run in Docker; external endpoints allowed only for Runpod vLLM
- Public port 5001; internal 5000; DB/Redis on internal networks only
- Secrets via env; no secrets committed

## Directory Hotspots
- `app/services/` (orchestration), `app/routes/api.py` (API), `scripts/eval/` (eval), `docker-compose*.yml` (deploy)

## Change Checklist (Fast)
- Changing model: update `LLM_MODEL` (and possibly `LLM_API_BASE_URL`), run admin warm, re-run 2-item eval smoke
- Changing router endpoint: set `LLM_API_BASE_URL`, confirm `/v1/models` reachable, run diagnostics
- Adding fields to analysis: map in `router_analyzer.py` normalize + service mapping, extend tests

## Current Database Schema (Key Tables)

### users
- id (PK, int)
- spotify_id (varchar(255), unique, not null)
- email (varchar(255), unique, null)
- display_name (varchar(255), null)
- access_token (varchar(1024), not null)
- refresh_token (varchar(1024), null)
- token_expiry (timestamp, not null)
- is_admin (boolean, default false, not null)
- created_at (timestamp, default now)
- updated_at (timestamp, default now, on update)

Indexes/constraints:
- unique(spotify_id)
- unique(email)

### playlists
- id (PK, int)
- owner_id (int, FK -> users.id, not null)
- spotify_id (varchar(255), not null)
- name (varchar(255), not null)
- description (text, null)
- spotify_snapshot_id (varchar(255), null)
- image_url (varchar(512), null)
- cover_collage_urls (json, null)
- track_count (int, null)
- has_flagged (boolean, default false, not null)
- last_analyzed (timestamp, null)
- overall_alignment_score (float, null)  // 0-100 scale
- last_synced_from_spotify (timestamp, null)
- created_at (timestamp, default now)
- updated_at (timestamp, default now, on update)

Indexes/constraints:
- unique(owner_id, spotify_id)  // per-user uniqueness
- idx(owner_id), idx(last_analyzed), idx(updated_at)

### songs
- id (PK, int)
- spotify_id (varchar(255), unique, not null)
- title (varchar(255), not null)
- artist (varchar(255), not null)
- album (varchar(255), null)
- duration_ms (int, null)
- lyrics (text, null)
- album_art_url (varchar(512), null)
- explicit (boolean, default false)
- last_analyzed (timestamp, null)
- last_analysis_result_id (int, FK -> analysis_results.id, null)  // pointer for O(1) latest
- created_at (timestamp, default now)
- updated_at (timestamp, default now, on update)

Indexes/constraints:
- unique(spotify_id)
- idx(explicit), idx(last_analyzed)

### playlist_songs (association)
- playlist_id (int, FK -> playlists.id, PK part)
- song_id (int, FK -> songs.id, PK part)
- track_position (int, not null)
- added_at_spotify (timestamp, null)
- added_by_spotify_user_id (varchar(255), null)

Indexes:
- idx(playlist_id)
- idx(song_id)
- idx(playlist_id, track_position)

### analysis_results
- id (PK, int)
- song_id (int, FK -> songs.id, not null)
- status (varchar(20), not null)  // pending|in_progress|completed|failed
- score (float, null)  // 0-100
- concern_level (varchar(50), null)  // low|medium|high
- themes (json, null)
- concerns (json, null)
- explanation (text, null)
- analyzed_at (timestamp, default now)
- error_message (text, null)
- purity_flags_details (json, null)
- positive_themes_identified (json, null)
- biblical_themes (json, null)
- supporting_scripture (json, null)
- verdict (varchar(50), null)
- purity_score (float, null)
- formation_risk (varchar(20), null)
- doctrinal_clarity (varchar(20), null)
- confidence (varchar(20), null)
- needs_review (boolean, default false)
- narrative_voice (varchar(20), null)
- lament_filter_applied (boolean, default false)
- framework_data (json, null)
- created_at (timestamp, default now)
- updated_at (timestamp, default now, on update)

Indexes/constraints:
- idx(song_id)
- idx(status)
- idx(concern_level)
- idx(song_id, created_at)
- idx(song_id, analyzed_at)
- check(status in ('pending','in_progress','completed','failed'))

### whitelist
- id (PK, int)
- user_id (int, FK -> users.id, not null)
- spotify_id (varchar(255), not null)
- item_type (varchar(50), not null)  // song|artist|playlist
- name (varchar(255), null)
- reason (text, null)
- added_date (timestamp, default now)

Indexes/constraints:
- unique(user_id, spotify_id, item_type)

### blacklist
- id (PK, int)
- user_id (int, FK -> users.id, not null)
- spotify_id (varchar(255), not null)
- item_type (varchar(50), not null)  // song|artist|playlist
- name (varchar(255), null)
- reason (text, null)
- added_date (timestamp, default now)

Indexes/constraints:
- unique(user_id, spotify_id, item_type)

### lyrics_cache
- id (PK, int)
- artist (varchar(255), not null, index)
- title (varchar(255), not null, index)
- lyrics (text, not null)
- source (varchar(50), not null)
- created_at (timestamp, default now)
- updated_at (timestamp, default now, on update)

Indexes/constraints:
- unique(artist, title)
- idx(artist, title), idx(source), idx(updated_at)

## Notes & Data Considerations
- Prefer reads via `Song.last_analysis_result_id` to avoid N+1 queries for latest results.
- Maintain `Playlist.has_flagged` on analysis completion; use admin recompute for audits.
- Keep JSON fields unindexed until a concrete query/filter requires it.
- Track counts: `playlists.track_count` is the single source of truth; `total_tracks` removed.
- Ownership uniqueness: `playlists (owner_id, spotify_id)` prevents cross-user collisions.
