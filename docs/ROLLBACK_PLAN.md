Rollback Plan (Router-only Migration)
====================================

Purpose
-------
Document a safe rollback path if the Router-only analyzer migration needs to be reverted after Runpod or local validation uncovers blocking issues.

Current State
-------------
- Analyzer: Router-only (OpenAI-compatible HTTP) via `RouterAnalyzer`
- Profiles: Ollama local, Runpod vLLM
- HF/transformers: removed from app code and requirements
- DB schema: unchanged (no new migrations)
- CI: offline-safe, Router HTTP mocked

Rollback Strategy
-----------------
Prefer a clean Git rollback rather than ad‑hoc file edits.

1) Identify baseline commit/branch (pre-migration)
   - Locate the last known-good baseline prior to Router-only changes.
   - Example placeholders: `baseline`, `router-migration`.

2) Switch back to baseline
   ```bash
   git switch baseline
   # or checkout by commit SHA
   # git switch --detach <SHA>
   ```

3) Rebuild environment
   - Docker:
     ```bash
     docker compose build --no-cache
     docker compose up -d
     ```
   - Local:
     ```bash
     python3 -m venv .venv && source .venv/bin/activate
     python3 -m pip install --upgrade pip
     python3 -m pip install -r requirements.txt
     ```

4) Sanity checks
   ```bash
   pytest -q
   # Optional quick eval smoke per that baseline’s flow
   # python -m scripts.eval.run_eval --input scripts/eval/smoke2.jsonl \
   #   --out scripts/eval/reports/reviews/$(date +%Y%m%d-%H%M%S)
   ```

5) Roll-forward plan
   - Keep `router-migration` branch intact while validating Runpod.
   - Once validated, merge and tag a release.
   - If fixes are needed, patch `router-migration`, retest, redeploy.

Operational Toggles (Mitigations)
---------------------------------
- Skip analyzer preflight/warmup (cold starts, CI, degraded router):
  ```bash
  export DISABLE_ANALYZER_PREFLIGHT=1
  ```
- CI-safe branch (already used in tests):
  ```bash
  export CI=1
  ```
- Router profile env:
  ```bash
  # Local (Ollama)
  export LLM_API_BASE_URL=http://host.docker.internal:11434/v1
  export LLM_MODEL=llama3.1:8b

  # Runpod (vLLM)
  export LLM_API_BASE_URL=http(s)://<runpod-host>:<port>/v1
  export LLM_MODEL=<llama-3.1-70b-instruct-awq>
  ```

Not Required During Rollback
----------------------------
- No database rollback; schema unchanged.
- No background migrations to halt.

If Remaining on Router-only Temporarily
--------------------------------------
- Switch models/endpoints to stabilize.
- Reduce load and increase resiliency:
  ```bash
  export LLM_CONCURRENCY=1
  export LLM_TIMEOUT=120
  ```
- Continue to run `pytest -q` and a 2‑item eval smoke before/after any change.

Validation Checklist (Post-Rollback)
------------------------------------
- App healthy on port 5001; key routes respond
- `pytest -q` green
- Quick eval smoke completes
- No unexpected Router-only references in the baseline branch

Notes
-----
- Use tags for clarity (e.g., `v-baseline`, `v-router-migration`) and switch with `git switch`.
- Avoid partial cherry-picks for rollback; prefer clean branch switches.

