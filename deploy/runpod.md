RunPod Deployment Notes

Environment variables (web):
- FLASK_ENV=production
- SECRET_KEY=... (32+ chars)
- DATABASE_URL=postgresql://user:pass@db:5432/app
- REDIS_URL=redis://redis:6379/0
- LLM_API_BASE_URL=https://<your-vllm-host>:8000/v1
- LLM_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
- ENABLE_RULES_RAG=1
- BACKFILL_WORKERS=3
- BACKFILL_BATCH_SIZE=25
- BACKFILL_AUTOBACKOFF=1
- BACKFILL_MIN_WORKERS=1
- BACKFILL_MIN_BATCH=5

vLLM pod:
- Image: vllm/vllm-openai:latest
- Command example:
  --model meta-llama/Meta-Llama-3.1-8B-Instruct --host 0.0.0.0 --port 8000 \
  --download-dir /data/models --gpu-memory-utilization 0.9
- Volumes: Persist /data/models
- Env: HUGGING_FACE_HUB_TOKEN=<your token>

First checks:
1) Call /api/admin/diagnostics – verify DB/Redis ok, LLM ready, RAG enabled
2) Call /api/admin/warm – build RAG + warm LLM
3) Start backfill from Settings; monitor /api/admin/backfill-status
