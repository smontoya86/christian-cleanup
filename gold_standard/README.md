# Gold Standard Evaluation Dataset

This directory contains the complete evaluation dataset, training data, scripts, and results for the Christian music analysis fine-tuning project.

---

## 📁 Directory Structure

### **documentation/**
Contains all markdown documentation, guides, and reports:
- `FINETUNE_4O_MINI_RESULTS.md` - Final evaluation results and analysis
- `BASELINE_METRICS_V3.md` - Baseline performance metrics
- `FINE_TUNING_SUMMARY.md` - Summary of fine-tuning process
- `MODEL_COMPARISON_GUIDE.md` - Guide for comparing models
- `SONG_SELECTION_GUIDE.md` - Guidelines for selecting songs
- `README.md` - Original eval README
- `dataset_expansion_plan.md` - Plans for expanding dataset
- `expansion_plan_30_songs.md` - 30-song expansion plan
- `gold_standard_gratitude.md` - Gratitude/acknowledgment notes

### **training_data/**
Contains the final training datasets used for fine-tuning:
- `training_data_1378_final.jsonl` - Complete labeled dataset (1,378 songs)
- `openai_finetune/` - OpenAI fine-tuning format files
  - `train.jsonl` - Training set (1,098 songs, 80%)
  - `validation.jsonl` - Validation set (138 songs, 10%)
  - `test.jsonl` - Hold-out test set (138 songs, 10%)

### **test_data/**
Contains test/validation datasets:
- `test_set_eval_format.jsonl` - Test set in evaluation format (138 songs)

### **scripts/**
Contains all Python and shell scripts used for dataset generation and evaluation:
- `generate_training_data.py` - Generate labeled training data using GPT-4o-mini
- `convert_to_openai_format.py` - Convert labeled data to OpenAI fine-tuning format
- `convert_openai_to_eval_format.py` - Convert OpenAI format back to eval format
- `run_eval.py` - Main evaluation script
- `test_finetune_4o_mini.sh` - Test fine-tuned model
- `analyze_results.sh` - Quick results summary
- `run_in_container.sh` - Run eval in Docker container

### **song_examples/**
Contains individual song analyses with detailed theological assessments:
- 31 example songs covering various verdicts and theological themes
- Includes both positive examples (hymns, worship songs) and negative examples (prosperity gospel, self-focused, etc.)

### **reports/**
Contains evaluation results and metrics:
- `final_evaluation/` - Final hold-out test results
  - `summary.json` - Overall metrics
  - `predictions.jsonl` - All predictions
  - `predictions.csv` - Predictions in CSV format
  - `report.html` - HTML report

---

## 🎯 Quick Start

### View Evaluation Results
```bash
cat gold_standard/documentation/FINETUNE_4O_MINI_RESULTS.md
```

### Run Quick Summary
```bash
./gold_standard/scripts/analyze_results.sh gold_standard/reports/final_evaluation
```

### View Training Data
```bash
head -1 gold_standard/training_data/training_data_1378_final.jsonl | jq .
```

### Test Fine-Tuned Model (requires Docker & OpenAI API key)
```bash
./gold_standard/scripts/test_finetune_4o_mini.sh
```

---

## 📊 Dataset Statistics

- **Total Songs:** 1,378
- **Training:** 1,098 (80%)
- **Validation:** 138 (10%)
- **Test:** 138 (10%)

### Verdict Distribution
- **freely_listen:** 32% (high-quality worship/hymns)
- **context_required:** 19% (mixed content, needs discernment)
- **caution_limit:** 27% (significant concerns, limit exposure)
- **avoid_formation:** 22% (harmful to spiritual formation)

### Genre Coverage
- Contemporary Christian (Hillsong, Bethel, Elevation)
- Classic Hymns (Amazing Grace, How Great Thou Art)
- Gospel (traditional & contemporary)
- Secular Pop/Rock (with Christian themes or concerns)
- Hip-Hop/Rap (Christian & secular)
- R&B/Soul
- Country
- Alternative/Indie

---

## 🎓 Key Metrics (Final Model)

| Metric | Score |
|--------|-------|
| **Verdict Accuracy** | **80.4%** |
| **Verdict F1-Score** | **79.1%** |
| **Score MAE** | **4.47 points** |
| **Pearson Correlation** | **0.967** |

**Per-Verdict Accuracy:**
- `freely_listen`: 100% (32/32)
- `avoid_formation`: 95.3% (41/43)
- `context_required`: 69.2% (18/26)
- `caution_limit`: 54.1% (20/37)

---

## 🔧 How This Dataset Was Created

1. **Initial Selection (300 songs)** - Manually curated diverse set
2. **GPT-4o-mini Labeling** - Used GPT-4o-mini with full Christian Framework v3.1 prompt
3. **Iterative Expansion (1,378 songs)** - Added songs to fill gaps and improve variance
4. **Quality Verification** - Reviewed labels for consistency and accuracy
5. **OpenAI Format Conversion** - Converted to fine-tuning format with full system prompt
6. **Fine-Tuning** - Trained gpt-4o-mini model on 1,098 songs
7. **Validation** - Tested on 138 hold-out songs

---

## 📝 Notes

- All songs were labeled using GPT-4o-mini with the **full Christian Framework v3.1 system prompt**
- Scripture references are mandatory for every song
- Common Grace recognition and Character Voice filters were applied
- Vague Spirituality cap (max 45 score) was enforced
- Training data includes extensive theological reasoning and analysis

---

## 🚀 Model Information

**Fine-Tuned Model ID:**
```
ft:gpt-4o-mini-2024-07-18:personal:christian-discernment-4o-mini-v1:CLxyepav
```

**API Endpoint:**
```
https://api.openai.com/v1/chat/completions
```

**Cost per Song:**
- ~$0.0006 USD (~3,500 input tokens + 250 output tokens)

---

## 📚 Related Documentation

- **Production Deployment:** `docs/PRODUCTION_DEPLOYMENT_4O_MINI.md`
- **Christian Framework:** `docs/biblical_discernment_v2.md`
- **System Architecture:** `docs/system_architecture.md`

---

**Last Updated:** October 1, 2025  
**Dataset Version:** 1.0  
**Model Version:** christian-discernment-4o-mini-v1

