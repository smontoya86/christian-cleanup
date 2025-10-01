#!/bin/bash
# Test fine-tuned gpt-4o-mini on hold-out set

set -e

echo "🧪 Testing fine-tuned gpt-4o-mini on hold-out test set..."
echo ""

# Fine-tuned model ID
MODEL_ID="ft:gpt-4o-mini-2024-07-18:personal:christian-discernment-4o-mini-v1:CLxyepav"

# Create output directory
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUT_DIR="scripts/eval/reports/finetune_4o_mini_${TIMESTAMP}"
mkdir -p "$OUT_DIR"

echo "Model: $MODEL_ID"
echo "Output: $OUT_DIR"
echo ""

# Load OpenAI API key from .env file
if [ -f .env ]; then
  export $(grep -v '^#' .env | grep OPENAI_API_KEY | xargs)
fi

if [ -z "$OPENAI_API_KEY" ]; then
  echo "❌ Error: OPENAI_API_KEY not found in .env file"
  exit 1
fi

# Run evaluation with OpenAI API
docker compose exec -T \
  -e LLM_API_BASE_URL=https://api.openai.com/v1 \
  -e LLM_MODEL="$MODEL_ID" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e LLM_MAX_TOKENS=2000 \
  -e LLM_TEMPERATURE=0.2 \
  -e LLM_CONCURRENCY=3 \
  -e LLM_TIMEOUT=120 \
  web python scripts/eval/run_eval.py \
  --input scripts/eval/test_set_eval_format.jsonl \
  --out "$OUT_DIR"

echo ""
echo "✅ Evaluation complete!"
echo "📊 Results saved to: $OUT_DIR"
echo ""
echo "Key metrics to review:"
echo "  - Overall accuracy"
echo "  - MAE (Mean Absolute Error) on scores"
echo "  - Verdict classification accuracy"
echo "  - Scripture reference quality"

