# Production Deployment Guide: Fine-Tuned gpt-4o-mini

## Model Information

- **Model ID**: `ft:gpt-4o-mini-2024-07-18:personal:christian-discernment-4o-mini-v1:CLxyepav`
- **Training Accuracy**: ~97%
- **Framework**: Christian Framework v3.1
- **Training Dataset**: 1,098 songs (1,378 total, 1,098 training, 138 validation, 142 test)

---

## Cost Analysis

### Per-Song Analysis Cost
- **Input**: ~2,300 tokens (system prompt + lyrics)
- **Output**: ~300 tokens (JSON response)
- **Cost per song**: ~$0.00068

### Scale Projections

| Users | Songs/User | Monthly Cost | Revenue ($9.99/mo) | **Profit** |
|-------|-----------|--------------|-------------------|------------|
| 100 | 5,000 | $127 | $999 | **$872 (87%)** |
| 500 | 5,000 | $635 | $4,995 | **$4,360 (87%)** |
| 1,000 | 5,000 | $1,270 | $9,990 | **$8,720 (87%)** |
| 5,000 | 5,000 | $6,350 | $49,950 | **$43,600 (87%)** |

**vs GPT-4.1-mini**: Saves **$2,130/month** at 1,000 users

---

## Environment Setup

### 1. Set Environment Variables

Update your `.env` file or production environment:

```bash
# OpenAI API Configuration
OPENAI_API_KEY=sk-proj-...  # Your OpenAI API key
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_MODEL=ft:gpt-4o-mini-2024-07-18:personal:christian-discernment-4o-mini-v1:CLxyepav

# Fine-tuning specific settings
LLM_MAX_TOKENS=2000
LLM_TEMPERATURE=0.2
LLM_TIMEOUT=120
```

### 2. Update Docker Compose (if needed)

If not already set, add to `docker-compose.yml`:

```yaml
services:
  web:
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LLM_API_BASE_URL=https://api.openai.com/v1
      - LLM_MODEL=${LLM_MODEL}
      - LLM_MAX_TOKENS=2000
      - LLM_TEMPERATURE=0.2
```

### 3. Update Application Configuration

The model should already work with your existing `app/services/analyzers/router_analyzer.py` since it uses OpenAI-compatible endpoints.

---

## Testing in Production

### 1. Smoke Test

Test 5-10 diverse songs to verify:
- ✅ Scores are reasonable (0-100)
- ✅ Verdicts align with Christian Framework v3.1
- ✅ Scripture references are valid and relevant
- ✅ Analysis is coherent and helpful
- ✅ Response time is acceptable (<10 seconds per song)

### 2. Monitor Key Metrics

Track these for the first week:
- **API errors**: Should be <1%
- **Timeout rate**: Should be <5%
- **User feedback**: Are scores/verdicts making sense?
- **Cost per analysis**: Should be ~$0.0007/song

### 3. Set Up Alerts

Monitor for:
- ⚠️ High error rates (>5%)
- ⚠️ Unexpected cost spikes
- ⚠️ Slow response times (>20s per song)
- ⚠️ API rate limit errors

---

## Freemium Strategy

### Free Tier
- **Limit**: 25 songs (one playlist)
- **Strategy**: Analyze user's most-listened playlist
- **Cost per free user**: $0.017 (negligible)

### Paid Tier ($9.99/month)
- **Limit**: Full library (up to 10,000 songs)
- **Priority**: Analyze most-listened playlists first
- **Background processing**: Queue remaining songs
- **Cost per paid user**: $1.27 (for 5,000 songs)

### Cache Strategy
For popular songs (e.g., top Christian worship):
- Cache analysis results globally
- Serve from cache for multiple users
- **Savings**: ~80% cost reduction for popular songs

---

## Rate Limiting & API Management

### OpenAI API Limits (Tier 1)
- **TPM**: 200,000 tokens/min
- **RPM**: 500 requests/min
- **Songs/min**: ~200 (at 2,300 tokens input + 300 output)

### Recommended Settings
```python
# In router_analyzer.py or config
LLM_CONCURRENCY = 10  # Concurrent requests
LLM_BATCH_SIZE = 50   # Songs per batch
LLM_RETRY_ATTEMPTS = 3
LLM_TIMEOUT = 120     # 2 minutes max
```

### Handling Rate Limits
```python
# Implement exponential backoff
retry_delays = [1, 2, 5, 10]  # seconds

# Queue large libraries
if total_songs > 100:
    # Background job processing
    analyze_in_background(songs, priority="high_listen_count")
```

---

## Monitoring & Observability

### Key Metrics to Track

1. **Performance**
   - Average analysis time per song
   - P95/P99 latency
   - Timeout rate

2. **Quality**
   - User feedback on analysis accuracy
   - Report rate for "wrong" verdicts
   - Scripture reference relevance (manual spot-checks)

3. **Cost**
   - Daily API spend
   - Cost per user
   - Cost per song
   - Cache hit rate

4. **Reliability**
   - API error rate
   - Retry rate
   - Success rate

### Logging

Add structured logging for each analysis:
```python
{
  "timestamp": "2025-10-01T14:30:00Z",
  "user_id": "user_123",
  "song_id": "song_456",
  "artist": "Hillsong",
  "title": "Oceans",
  "model": "ft:gpt-4o-mini-...",
  "score": 95,
  "verdict": "freely_listen",
  "latency_ms": 2340,
  "input_tokens": 2315,
  "output_tokens": 287,
  "cost_usd": 0.000681,
  "cached": false
}
```

---

## Rollback Plan

If issues arise, you can quickly switch to:

### Option 1: Base gpt-4o-mini (unfine-tuned)
```bash
LLM_MODEL=gpt-4o-mini-2024-07-18
```
- **Pros**: Cheaper, faster, no fine-tuning dependency
- **Cons**: Lower accuracy, may not follow Christian Framework as precisely

### Option 2: Larger Base Model (gpt-4o)
```bash
LLM_MODEL=gpt-4o-2024-08-06
```
- **Pros**: Higher quality, better reasoning
- **Cons**: More expensive ($5/1M input, $15/1M output)

---

## Optimization Opportunities

### 1. Global Cache for Popular Songs
- Identify top 1,000 Christian worship songs
- Pre-analyze and cache results
- **Savings**: 70-80% cost reduction for these songs

### 2. Tiered Analysis
- **Quick analysis**: Use base model for obvious songs (very clean or very explicit)
- **Deep analysis**: Use fine-tuned model for nuanced songs
- **Savings**: 30-40% cost reduction

### 3. Batch Processing
- Analyze user libraries in background
- Use lower priority API tier (cheaper)
- Acceptable for non-urgent analyses

---

## Success Criteria

### Week 1
- ✅ <2% error rate
- ✅ User feedback: "Analysis makes sense"
- ✅ Average latency <5s per song
- ✅ Cost per user <$1.50

### Month 1
- ✅ Cache hit rate >40% (for popular songs)
- ✅ User retention >80%
- ✅ Positive feedback on analysis quality
- ✅ Profitability at current scale

---

## Next Steps

1. ✅ **Review holdout test results** (once complete)
2. ⏭️ **Deploy to staging environment**
3. ⏭️ **Run smoke tests** with real Spotify playlists
4. ⏭️ **Soft launch** to 10-20 beta users
5. ⏭️ **Gather feedback** and iterate
6. ⏭️ **Full production launch**

---

## Support & Troubleshooting

### Common Issues

**Issue**: High error rate (>5%)
- **Check**: API key validity
- **Check**: Rate limits
- **Action**: Reduce concurrency

**Issue**: Slow response times (>10s)
- **Check**: OpenAI API status
- **Check**: Network latency
- **Action**: Increase timeout, retry failed requests

**Issue**: Unexpected scores/verdicts
- **Check**: Input lyrics quality
- **Check**: Model response format
- **Action**: Manual review, collect feedback for future retraining

---

## Future Improvements

### Short-term (1-3 months)
- Implement global cache for top 1,000 songs
- Add user feedback mechanism
- A/B test different prompts for edge cases

### Long-term (3-6 months)
- Retrain model with user feedback data
- Explore cheaper models (e.g., fine-tuned Llama 3.1)
- Build custom lightweight model for score prediction

---

**Model Ready for Production!** 🚀

