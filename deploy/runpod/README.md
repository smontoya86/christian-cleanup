Runpod Deployment (vLLM + Qwen2.5-14B-Instruct AWQ)
===================================================

Steps
-----
1) Start interactive pod (L4) and bulk pod (L40S) separately.
   - Interactive: use `vllm_qwen14b_awq_start.sh` (port 8000 inside container; map to e.g. 8000)
   - Bulk: use `vllm_qwen14b_awq_start_bulk.sh` (port 8000 inside container; map to e.g. 8001)

2) In Runpod UI, open each pod → Networking tab and note the external URL/port (or proxy URL).

3) Update environment (.env used by docker-compose `env_file`):
   - `USE_LLM_ANALYZER=1`
   - `LLM_INTERACTIVE_API_BASE_URL=http://<interactive-host>:<interactive-port>/v1`
   - `LLM_BULK_API_BASE_URL=http://<bulk-host>:<bulk-port>/v1`
   - `LLM_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ`
   - Optionally set per-endpoint models with `LLM_INTERACTIVE_MODEL` and `LLM_BULK_MODEL`.

   Then restart web container:
   ```bash
   docker compose up -d web --force-recreate
   ```

4) Verify router:
   - `GET /admin/llm-router` (must be admin)
   - `GET /admin/llm-router?batch_size=100` (expect interactive)
   - `GET /admin/llm-router?batch_size=500` (expect bulk)

Notes
-----
- Increase `--max-num-seqs` and GPU utilization for bulk throughput; keep interactive responsive.
- Ensure one interactive pod stays warm to avoid cold-start latency.
- vLLM exposes OpenAI-compatible API at `/v1`.

Admin router check (inside web):
```bash
curl -s "http://localhost:5001/admin/llm-router?batch_size=200"
```

