#!/bin/bash
# Test fine-tuned GPT-4.1-mini on hold-out set

set -e

echo "🧪 Testing fine-tuned GPT-4.1-mini on hold-out test set..."
echo ""

# TODO: Replace with your GPT-4.1-mini model ID from OpenAI
MODEL_ID="ft:gpt-4.1-mini-2025-04-14:personal:YOUR_JOB_NAME:YOUR_JOB_ID"

# Create output directory
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUT_DIR="scripts/eval/reports/finetune_4.1_mini_${TIMESTAMP}"
mkdir -p "$OUT_DIR"

# Run evaluation
docker compose exec -T web python scripts/eval/run_eval.py \
  --input scripts/eval/openai_finetune/test.jsonl \
  --out "$OUT_DIR" \
  --model "$MODEL_ID"

echo ""
echo "✅ Evaluation complete!"
echo "📊 Results saved to: $OUT_DIR"
echo ""
echo "Key metrics to review:"
echo "  - Overall accuracy"
echo "  - MAE (Mean Absolute Error) on scores"
echo "  - Verdict classification accuracy"
echo "  - Scripture reference quality"

