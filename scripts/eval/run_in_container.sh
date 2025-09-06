#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   scripts/eval/run_in_container.sh [INPUT_JSONL] [OUT_DIR]
# Defaults:
#   INPUT_JSONL=scripts/eval/songs_eval.jsonl
#   OUT_DIR=scripts/eval/reports
# Env overrides (Router-only, OpenAI-compatible HTTP):
#   LLM_API_BASE_URL (default http://host.docker.internal:11434/v1)
#   LLM_MODEL       (default llama3.1:8b)
#   LLM_MAX_TOKENS  (default 2000)
#   LLM_TEMPERATURE (default 0.2)
#   LLM_CONCURRENCY (default 1)

INPUT=${1:-scripts/eval/songs_eval.jsonl}
OUT_BASE=${2:-scripts/eval/reports}
# Create timestamped run directory under reviews/
TS=$(date +%Y%m%d-%H%M%S)
RUN_DIR="$OUT_BASE/reviews/$TS"
mkdir -p "$RUN_DIR"
API_BASE=${LLM_API_BASE_URL:-http://host.docker.internal:11434/v1}
MODEL=${LLM_MODEL:-llama3.1:8b}
MAXTOK=${LLM_MAX_TOKENS:-2000}
TEMP=${LLM_TEMPERATURE:-0.2}
CONC=${LLM_CONCURRENCY:-1}

docker compose exec -T \
  -e PYTHONPATH=/app \
  -e LLM_API_BASE_URL="${API_BASE}" \
  -e LLM_MODEL="${MODEL}" \
  -e LLM_MAX_TOKENS="${MAXTOK}" \
  -e LLM_TEMPERATURE="${TEMP}" \
  -e LLM_CONCURRENCY="${CONC}" \
  web python scripts/eval/run_eval.py --input "${INPUT}" --out "${RUN_DIR}"

# Write simple metadata for the run
cat > "${RUN_DIR}/meta.json" <<META
{
  "timestamp": "${TS}",
  "input": "${INPUT}",
  "model": "${MODEL}",
  "api_base": "${API_BASE}",
  "max_tokens": ${MAXTOK},
  "temperature": ${TEMP},
  "concurrency": ${CONC}
}
META

echo "Eval completed. Reports in ${RUN_DIR}."


