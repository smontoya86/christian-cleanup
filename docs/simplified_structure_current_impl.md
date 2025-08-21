# Simplified Structure — Current Implementation

## Overview
- Flask app with blueprints: `auth`, `main`, `api`
- Services: Spotify integration, analysis orchestration, scripture mapping, concern detection
- Data: PostgreSQL via SQLAlchemy 2.0; Redis for cache/sessions
- Deployment: Docker + Compose; CI via GitHub Actions; lint/tests via pre-commit/pytest

## Request Flow (high level)
1. User authenticates (Spotify OAuth or mock)
2. UI requests analysis data via `/api/...`
3. Analysis service computes or fetches cached results
4. Response includes verdict, themes, scripture, concerns, and scores

## Key Modules
- `app/routes/`
  - `main.py`: dashboard and pages
  - `api.py`: JSON endpoints (analysis, whitelist, status)
  - `auth.py`: login/logout
- `app/services/`
  - `unified_analysis_service.py`: orchestrates analysis
  - `simplified_christian_analysis_service.py`: model-driven analysis
  - `enhanced_scripture_mapper.py`, `enhanced_concern_detector.py`
- `app/models/models.py`: SQLAlchemy models for songs/playlists/analyses
- `app/utils/`: validation, correlation IDs, health, retry, lyrics fetching

## Data Model (essentials)
- `Song(id, title, artist, album, lyrics, ...)`
- `AnalysisResult(song_id, status, score, concern_level, themes, problematic_content, created_at, ...)`
- `Playlist`, `PlaylistSong`
- `Whitelist`

## Reliability & Observability
- Correlation ID via `X-Request-ID` header
- User-scoped rate limiting in production
- Metrics: Prometheus exporter integrated

## CI/CD
- CI: lint (ruff) + tests on PRs and pushes
- Release: tag `v*` builds/pushes Docker image to GHCR

## Local Development
- Use Docker Compose; see README for commands
- Run tests with `pytest -q`
- Lint/format with `pre-commit run -a`

## Notes
- Emergency analysis path is retained behind env flag
- Timezone-aware datetimes used throughout
