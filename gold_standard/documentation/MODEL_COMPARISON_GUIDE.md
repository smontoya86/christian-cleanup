# Fine-Tuned Model Comparison Guide

## Models Being Tested

### gpt-4o-mini
- **Model ID**: `ft:gpt-4o-mini-2024-07-18:personal:christian-discernment-4o-mini-v1:CLxyepav`
- **Training Accuracy**: ~97%
- **Training Loss**: 0.096
- **Inference Cost**: $0.30/1M input + $1.20/1M output tokens

### GPT-4.1-mini
- **Model ID**: [Add your GPT-4.1-mini model ID here]
- **Training Accuracy**: 97.3%
- **Training Loss**: 0.085
- **Inference Cost**: $0.80/1M input + $3.20/1M output tokens

---

## How to Run Tests

### 1. Test gpt-4o-mini
```bash
./scripts/eval/test_finetune_4o_mini.sh
```

### 2. Test GPT-4.1-mini
First, update `test_finetune_4_1_mini.sh` with your GPT-4.1-mini model ID, then:
```bash
./scripts/eval/test_finetune_4_1_mini.sh
```

---

## What to Compare

### 1. Overall Accuracy
- **Location**: Check the summary report in each output directory
- **What to look for**: How often does the model predict the correct score/verdict?
- **Threshold**: If difference is <3%, choose gpt-4o-mini for cost savings

### 2. Score Accuracy (MAE)
- **Metric**: Mean Absolute Error
- **What it means**: Average difference between predicted and actual scores (0-100 scale)
- **Good**: MAE < 10 (within 10 points on average)
- **Excellent**: MAE < 5

### 3. Verdict Classification
- **Categories**: freely_listen, context_required, caution_limit, avoid_formation
- **What to check**: How often does the model put songs in the correct category?
- **Critical**: Avoid false negatives (marking harmful content as safe)

### 4. Scripture References
- **Manual Review**: Spot-check 10-20 songs
- **Questions to ask**:
  - Are scripture references relevant to the song's content?
  - Are they theologically accurate?
  - Do they support the verdict/score?

### 5. Analysis Quality
- **Manual Review**: Read the "analysis" field for 10-20 songs
- **Questions to ask**:
  - Does the explanation make sense?
  - Does it align with Christian Framework v3.1?
  - Is it helpful for users?

---

## Decision Matrix

| Scenario | Recommendation |
|----------|---------------|
| **gpt-4o-mini accuracy within 2% of GPT-4.1-mini** | ✅ **Use gpt-4o-mini** (cost savings justify it) |
| **gpt-4o-mini accuracy 2-4% behind** | 🟡 **Probably use gpt-4o-mini** (still excellent, saves $2k/month) |
| **gpt-4o-mini accuracy 4-6% behind** | 🟡 **Tough call** (consider target market - premium users vs mass market) |
| **gpt-4o-mini accuracy >6% behind** | 🔴 **Consider GPT-4.1-mini** (quality gap might matter) |

---

## Cost Impact (at 1,000 paid users)

### Monthly Inference Costs
- **gpt-4o-mini**: $1,270
- **GPT-4.1-mini**: $3,400
- **Savings with gpt-4o-mini**: $2,130/month

### Annual Savings
- **$25,560/year** with gpt-4o-mini

### Profit Margins (at $9.99/month subscription)
- **gpt-4o-mini**: 87% margin ($8,720 profit)
- **GPT-4.1-mini**: 66% margin ($6,590 profit)

---

## Next Steps After Testing

### If Choosing gpt-4o-mini (Recommended):
1. Update `app/config_llm.py` or set `LLM_MODEL` env var
2. Set `OPENAI_API_KEY` in production environment
3. Deploy to production
4. Monitor initial user feedback
5. Track accuracy metrics in production

### If Choosing GPT-4.1-mini:
- Same steps as above, but with GPT-4.1-mini model ID
- Consider offering both as "Standard" vs "Premium" tiers

### Optional: A/B Testing
- Use gpt-4o-mini for 80% of users
- Use GPT-4.1-mini for 20% of users
- Compare user satisfaction and churn rates
- Make final decision based on real user data

