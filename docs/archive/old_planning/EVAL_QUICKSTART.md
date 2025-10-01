# Evaluation Quick Start

## What We've Set Up

### ✅ Model Configuration
- **Updated to qwen3:8b** in `app/config_llm.py`
- **Model pulled** via Ollama (`ollama pull qwen3:8b`)
- **Local inference** configured for zero marginal cost

### ✅ Evaluation Infrastructure
- **Baseline eval set**: 10 songs covering all verdict tiers (`scripts/eval/baseline_10_template.jsonl`)
- **Lyrics fetcher script**: `scripts/eval/fetch_baseline_lyrics.py`
- **Eval runner**: `scripts/eval/run_in_container.sh`
- **Documentation**: `docs/EVALUATION_GUIDE.md`

### ✅ Production Strategy
- **Freemium model**: 1 playlist, 25 songs max
- **Paid tier**: $9.99/month, all playlists
- **Global cache**: 60-80% cost savings
- **Fine-tuning path**: $150-200 one-time for 90-95% accuracy

---

## Next Steps (Once Docker is Running)

### Step 1: Fetch Baseline Lyrics

```bash
# Use your existing lyrics fetching infrastructure
docker compose exec web python scripts/eval/fetch_baseline_lyrics.py
```

This will create `scripts/eval/baseline_10.jsonl` with lyrics fetched from:
- LRCLib (primary)
- Lyrics.ovh (fallback)
- Genius (last resort)

### Step 2: Run Baseline Evaluation

```bash
# Run eval with qwen3:8b and 10 concurrent requests
LLM_MODEL=qwen3:8b \
LLM_CONCURRENCY=10 \
scripts/eval/run_in_container.sh scripts/eval/baseline_10.jsonl
```

**Expected duration**: ~2-3 minutes for 10 songs

### Step 3: Review Results

Results saved to `scripts/eval/reports/reviews/<timestamp>/`:

```bash
# View summary
cat scripts/eval/reports/reviews/<timestamp>/summary.json

# View detailed predictions
cat scripts/eval/reports/reviews/<timestamp>/predictions.csv
```

**Key Metrics to Check**:
- **Verdict Accuracy**: Should be ≥85% for production
- **Score MAE**: Should be ≤12 points
- **Concern F1**: Should be ≥0.80

### Step 4: Decision Point

**If accuracy ≥85%**:
✅ Ship it! Use qwen3:8b in production

**If accuracy 75-84%**:
⚠️ Expand to 50 songs, validate consistency, consider fine-tuning

**If accuracy <75%**:
❌ Review system prompt, expand eval set to 150 songs, fine-tune model

---

## Baseline Song Coverage

The 10-song baseline covers:

| Category | Songs | Purpose |
|----------|-------|---------|
| **Freely Listen (90-100)** | Amazing Grace, Oceans | Clear Christian content |
| **Context Required (70-89)** | Reckless Love, You Say, Held, Stressed Out | Theological nuance |
| **Caution/Limit (50-69)** | Believer, Fight Song | Self-focus, vague spirituality |
| **Avoid Formation (0-49)** | Imagine, Highway to Hell | Anti-Christian, explicit rebellion |

**Genre diversity**: Hymns, worship, CCM, pop, rock
**Framework features tested**: Lament filter, theological precision, concern detection

---

## Troubleshooting

### Docker Containers Not Starting

```bash
# Check logs
docker compose logs web --tail 50

# Rebuild if needed
docker compose build web --no-cache
docker compose up -d
```

### Lyrics Not Fetching

Check if Genius API key is configured (optional but improves success rate):

```bash
# Add to .env file
LYRICSGENIUS_API_KEY=your-key-here
```

### Model Not Found

```bash
# Verify Ollama has the model
ollama list | grep qwen3

# Pull if missing
ollama pull qwen3:8b
```

### Slow Evaluation

Increase concurrency:

```bash
LLM_CONCURRENCY=20 scripts/eval/run_in_container.sh baseline_10.jsonl
```

---

## After Baseline Eval

### Option A: Expand to 50 Songs

```bash
docker compose exec web python scripts/eval/build_golden_set.py \
  --input scripts/eval/golden_eval_starter_50.md \
  --output scripts/eval/golden_50.jsonl
```

### Option B: Fine-Tune (if accuracy <85%)

See `docs/EVALUATION_GUIDE.md` section on "Fine-Tuning Workflow"

**Estimated cost**: $150-200 one-time
**Expected improvement**: 80% → 95% accuracy

---

## Files Created

- `app/config_llm.py` - Updated to qwen3:8b
- `scripts/eval/fetch_baseline_lyrics.py` - Lyrics fetching script
- `scripts/eval/baseline_10_template.jsonl` - Song list (awaiting lyrics)
- `scripts/eval/golden_eval_starter_50.md` - 50-song expansion list
- `docs/EVALUATION_GUIDE.md` - Complete eval documentation
- `PRODUCTION_STRATEGY.md` - Freemium model & costs
- `EVAL_QUICKSTART.md` - This file

---

## Questions?

See:
- Full evaluation guide: `docs/EVALUATION_GUIDE.md`
- Production strategy: `PRODUCTION_STRATEGY.md`
- Song recommendations: `scripts/eval/golden_eval_starter_50.md`
