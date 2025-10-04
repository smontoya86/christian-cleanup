#!/usr/bin/env bash
set -euo pipefail

# Minimal smoke: router unit, core services, and critical functionality
export CI=1
export DISABLE_ANALYZER_PREFLIGHT=1
export FLASK_ENV=testing
export PYTHONPATH=.

pytest -q \
  tests/unit/test_router_analyzer.py \
  tests/unit/test_models.py \
  tests/unit/test_analysis_service.py \
  tests/test_queue_helpers.py \
  -q

