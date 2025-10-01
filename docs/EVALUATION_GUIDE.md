# Evaluation Guide

## Overview

This guide covers the evaluation workflow for testing and validating the Christian music analysis system. Evaluation helps measure model accuracy, identify areas for improvement, and ensure consistent quality.

---

## Quick Start

### 1. Pull the Model

```bash
ollama pull qwen3:8b
```

### 2. Create Baseline Eval Set

```bash
# Fetch lyrics for 10 baseline songs (requires Docker running)
docker compose exec web python scripts/eval/fetch_baseline_lyrics.py
```

This creates `scripts/eval/baseline_10.jsonl` with 10 songs covering:
- **Clearly Christian** (2 songs): Amazing Grace, Oceans
- **Context Required** (4 songs): Reckless Love, You Say, Held, Stressed Out  
- **Caution/Limit** (2 songs): Believer, Fight Song
- **Avoid Formation** (2 songs): Imagine, Highway to Hell

### 3. Run Evaluation

```bash
# Run eval with qwen3:8b model
LLM_MODEL=qwen3:8b \
LLM_CONCURRENCY=10 \
scripts/eval/run_in_container.sh scripts/eval/baseline_10.jsonl
```

### 4. Review Results

Results are saved to `scripts/eval/reports/reviews/<timestamp>/`:
- `summary.json` - Overall metrics (accuracy, F1, MAE)
- `predictions.csv` - Per-song predictions vs ground truth
- `report.html` - Visual comparison report

---

## Model Configuration

### Current Model: qwen3:8b

**Configuration** (`app/config_llm.py`):
```python
llm_config = {
    "default": "ollama",
    "providers": {
        "ollama": {
            "api_base": "http://localhost:11434/v1",
            "model": "qwen3:8b"
        }
    }
}
```

**Performance Characteristics**:
- Speed: ~5 seconds per song on M1 Max
- Quality: Expected 80-85% accuracy (baseline)
- Context window: 32K tokens
- Fine-tunable: Yes

### Alternative Models

To test with different models:

```bash
# Test with llama3.1:8b
LLM_MODEL=llama3.1:8b scripts/eval/run_in_container.sh baseline_10.jsonl

# Test with larger model (requires more RAM)
LLM_MODEL=qwen3:14b scripts/eval/run_in_container.sh baseline_10.jsonl
```

---

## Evaluation Metrics

### Verdict Accuracy
Measures how often the model's verdict (freely_listen, context_required, etc.) matches ground truth.

**Target**: ≥85% for production readiness

### Score MAE (Mean Absolute Error)
Average difference between predicted and actual scores (0-100 scale).

**Target**: ≤12 points for production readiness

### Concern Detection F1
Precision and recall for detecting concern categories.

**Target**: ≥0.80 F1 score for production readiness

### Scripture Reference Jaccard
Overlap between predicted and expected scripture references.

**Target**: ≥0.60 for production readiness

---

## Building Larger Eval Sets

### Option 1: Expand Baseline (50 songs)

Use the curated 50-song list:

```bash
# Fetch lyrics for 50 songs
docker compose exec web python scripts/eval/build_golden_set.py \
  --input scripts/eval/golden_eval_starter_50.md \
  --output scripts/eval/golden_50_unlabeled.jsonl

# Manually add ground truth labels
# Then run eval
scripts/eval/run_in_container.sh scripts/eval/golden_50.jsonl
```

### Option 2: Export from Database

If you have analyzed songs in your database:

```bash
# Export 100 songs with analysis
docker compose exec web python scripts/eval/export_eval_from_db.py --limit 100

# Review and validate labels
# Then run eval
scripts/eval/run_in_container.sh scripts/eval/songs_eval_db.jsonl
```

---

## Fine-Tuning Workflow

Once you have 150+ labeled songs with validated accuracy:

### 1. Prepare Training Data

```bash
docker compose exec web python scripts/prepare_training_data.py \
  --input scripts/eval/golden_150.jsonl \
  --output qwen3_training.jsonl \
  --split 0.8  # 80% train, 20% validation
```

### 2. Fine-Tune on RunPod

```bash
# Spin up RunPod A100 80GB instance
# Cost: ~$3/hour, 4-6 hours = $12-18

python train_qwen3.py \
  --model Qwen/Qwen3-8B \
  --data qwen3_training.jsonl \
  --epochs 3 \
  --lr 2e-5 \
  --output models/qwen3-8b-christian-v1
```

### 3. Validate Fine-Tuned Model

```bash
# Test on held-out validation set
LLM_MODEL=qwen3-8b-christian-v1 \
scripts/eval/run_in_container.sh scripts/eval/golden_validation.jsonl
```

**Expected Improvement**:
- Raw qwen3:8b: 80-85% accuracy
- Fine-tuned qwen3:8b: 90-95% accuracy

---

## Interpreting Results

### Good Results
```
Verdict Accuracy: 87%
Score MAE: 10.5
Concern F1: 0.82
Scripture Jaccard: 0.65
```
**Decision**: Ship it! Model is production-ready.

### Marginal Results
```
Verdict Accuracy: 75%
Score MAE: 18.2
Concern F1: 0.68
Scripture Jaccard: 0.45
```
**Decision**: Expand eval set to 150 songs, fine-tune model.

### Poor Results
```
Verdict Accuracy: 62%
Score MAE: 25.5
Concern F1: 0.52
Scripture Jaccard: 0.30
```
**Decision**: Check system prompt, review framework, consider larger base model.

---

## Performance Optimization

### Batching

Increase concurrency for faster eval runs:

```bash
# Default: 1 concurrent request
LLM_CONCURRENCY=10 scripts/eval/run_in_container.sh baseline_10.jsonl

# Aggressive (if you have RAM)
LLM_CONCURRENCY=20 scripts/eval/run_in_container.sh baseline_10.jsonl
```

**Speed Impact**:
- Sequential (concurrency=1): ~50 seconds per song
- Batched (concurrency=10): ~5-8 seconds per song
- Batched (concurrency=20): ~3-5 seconds per song

### Caching

For repeated evals, results are cached automatically. Clear cache with:

```bash
docker compose exec web python -c "from app.extensions import cache; cache.clear()"
```

---

## Troubleshooting

### Model Not Found

```bash
# Pull the model
ollama pull qwen3:8b

# Verify it's available
ollama list | grep qwen3
```

### Lyrics Not Fetching

```bash
# Check lyrics service
docker compose exec web python -c "
from app import create_app
from app.utils.lyrics.lyrics_fetcher import LyricsFetcher
app = create_app()
with app.app_context():
    fetcher = LyricsFetcher()
    lyrics = fetcher.get_lyrics('Amazing Grace', 'John Newton')
    print(f'Found: {len(lyrics) if lyrics else 0} chars')
"
```

### Slow Evaluation

- Check `LLM_CONCURRENCY` setting (increase to 10-20)
- Verify Ollama is using GPU (if available)
- Consider smaller eval set for quick iterations

---

## Best Practices

1. **Start Small**: Validate on 10 songs before scaling to 150
2. **Diverse Coverage**: Include all verdict tiers and concern categories
3. **Manual Review**: Verify ground truth labels are accurate
4. **Iterate**: Run evals after each framework change
5. **Document**: Track model version, prompt changes, and results
6. **Version Control**: Commit eval sets and results for reproducibility

---

## Next Steps

After running baseline eval:

1. **If accuracy ≥85%**: Deploy to production with current model
2. **If accuracy 75-84%**: Expand eval set and fine-tune
3. **If accuracy <75%**: Review system prompt and framework

See [PRODUCTION_STRATEGY.md](../PRODUCTION_STRATEGY.md) for deployment guidance.
