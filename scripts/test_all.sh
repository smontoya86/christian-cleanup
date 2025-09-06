#!/usr/bin/env bash
set -euo pipefail

# CI-friendly test runner
export CI=${CI:-1}
export DISABLE_ANALYZER_PREFLIGHT=${DISABLE_ANALYZER_PREFLIGHT:-1}
export FLASK_ENV=${FLASK_ENV:-testing}
export PYTHONPATH=${PYTHONPATH:-.}

# Run full test suite
pytest -q

