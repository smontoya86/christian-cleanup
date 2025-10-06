#!/bin/bash
# Run evaluation against production fine-tuned model

set -e

# Load OPENAI_API_KEY from .env (safer than exporting all vars)
if [ -f .env ]; then
    export OPENAI_API_KEY=$(grep '^OPENAI_API_KEY=' .env | cut -d '=' -f2- | tr -d '"')
fi

export LLM_API_BASE_URL="https://api.openai.com/v1"
export LLM_MODEL="ft:gpt-4o-mini-2024-07-18:personal:christian-discernment-4o-mini-v1:CLxyepav"
export LLM_TEMPERATURE="0.2"
export LLM_MAX_TOKENS="2000"
export LLM_TIMEOUT="180"
export LLM_CONCURRENCY="3"

# Verify API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "ERROR: OPENAI_API_KEY not found in .env file"
    exit 1
fi

echo "🚀 Running evaluation against fine-tuned model: $LLM_MODEL"
echo "📊 Test set: gold_standard/test_data/test_set_eval_format.jsonl"
echo "📁 Output: gold_standard/reports/current_prompt_eval"
echo ""

docker-compose exec -T -e LLM_API_BASE_URL -e LLM_MODEL -e LLM_TEMPERATURE -e LLM_MAX_TOKENS -e LLM_TIMEOUT -e LLM_CONCURRENCY -e OPENAI_API_KEY web python3 gold_standard/scripts/run_eval.py \
  --input gold_standard/test_data/test_set_eval_format.jsonl \
  --out gold_standard/reports/current_prompt_eval

echo ""
echo "✅ Evaluation complete!"
echo "📊 View results: gold_standard/reports/current_prompt_eval/report.html"

