#!/usr/bin/env bash
set -euo pipefail

# Minimal smoke: router unit, API E2E smoke, and critical services
export CI=1
export DISABLE_ANALYZER_PREFLIGHT=1
export FLASK_ENV=testing
export PYTHONPATH=.

pytest -q \
  tests/unit/test_router_analyzer.py \
  tests/unit/test_router_analyzer_errors.py \
  tests/integration/api/test_api_e2e_smoke.py \
  tests/services/test_analysis_service.py \
  -q

