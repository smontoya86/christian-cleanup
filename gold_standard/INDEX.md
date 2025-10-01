# Gold Standard - Quick Reference Index

Fast access to key files and documentation.

---

## 🎯 **Essential Files**

### 📊 **Evaluation Results**
- [**Final Evaluation Results**](documentation/FINETUNE_4O_MINI_RESULTS.md) ⭐
  - 80.4% verdict accuracy, 4.47 MAE, 96.7% correlation
  - Production-ready model performance analysis

### 📚 **Documentation**
- [**Main README**](README.md) - Overview and directory structure
- [**Fine-Tuning Summary**](documentation/FINE_TUNING_SUMMARY.md) - Training process and costs
- [**Model Comparison Guide**](documentation/MODEL_COMPARISON_GUIDE.md) - gpt-4o-mini vs gpt-4.1-mini
- [**Baseline Metrics**](documentation/BASELINE_METRICS_V3.md) - Pre-fine-tuning performance
- [**Song Selection Guide**](documentation/SONG_SELECTION_GUIDE.md) - How to choose evaluation songs

### 💾 **Datasets**
- [**Training Dataset**](training_data/training_data_1378_final.jsonl) - 1,378 labeled songs
- [**OpenAI Train Set**](training_data/openai_finetune/train.jsonl) - 1,098 songs (80%)
- [**OpenAI Validation Set**](training_data/openai_finetune/validation.jsonl) - 138 songs (10%)
- [**OpenAI Test Set**](training_data/openai_finetune/test.jsonl) - 138 songs (10%)
- [**Test Set (Eval Format)**](test_data/test_set_eval_format.jsonl) - Hold-out test set

### 🔧 **Scripts**
- [**Generate Training Data**](scripts/generate_training_data.py) - Label songs with GPT-4o-mini
- [**Run Evaluation**](scripts/run_eval.py) - Evaluate model performance
- [**Test Fine-Tuned Model**](scripts/test_finetune_4o_mini.sh) - Quick model test
- [**Analyze Results**](scripts/analyze_results.sh) - Quick summary of eval results

### 📁 **Reports**
- [**Final Evaluation Report**](reports/final_evaluation/summary.json) - Metrics JSON
- [**Predictions**](reports/final_evaluation/predictions.csv) - All model predictions
- [**HTML Report**](reports/final_evaluation/report.html) - Visual report

### 🎵 **Song Examples**
- [**Song Examples README**](song_examples/README.md) - Overview of 31 reference songs
- [**Amazing Grace**](song_examples/amazing_grace.md) - Classic hymn example
- [**Monster**](song_examples/monster.md) - Dark themes with character voice
- [**Reckless Love**](song_examples/reckless_love.md) - Theological concern example

---

## 🚀 **Quick Actions**

### View Final Results
```bash
cat gold_standard/documentation/FINETUNE_4O_MINI_RESULTS.md
```

### Run Quick Summary
```bash
./gold_standard/scripts/analyze_results.sh gold_standard/reports/final_evaluation
```

### View Sample Training Data
```bash
head -1 gold_standard/training_data/training_data_1378_final.jsonl | jq .
```

### Test Model (requires Docker + OpenAI API)
```bash
cd gold_standard/scripts
./test_finetune_4o_mini.sh
```

---

## 📊 **Key Metrics Summary**

| Metric | Value |
|--------|-------|
| **Total Songs** | 1,378 |
| **Verdict Accuracy** | 80.4% |
| **Score MAE** | 4.47 points |
| **Pearson Correlation** | 0.967 |
| **freely_listen Accuracy** | 100% |
| **avoid_formation Accuracy** | 95.3% |
| **Cost per Song** | $0.0006 |

---

## 🎯 **Model Information**

**Fine-Tuned Model ID:**
```
ft:gpt-4o-mini-2024-07-18:personal:christian-discernment-4o-mini-v1:CLxyepav
```

**Recommended for Production:** ✅ YES

---

## 🔗 **Related Documentation**

External to this folder:
- `docs/PRODUCTION_DEPLOYMENT_4O_MINI.md` - Production deployment guide
- `docs/biblical_discernment_v2.md` - Christian Framework v3.1
- `docs/system_architecture.md` - Application architecture
- `app/config_llm.py` - LLM configuration file

---

**Last Updated:** October 1, 2025  
**Version:** 1.0

