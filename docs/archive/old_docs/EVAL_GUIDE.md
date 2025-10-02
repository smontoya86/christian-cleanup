# Evaluation Guide (Router-only)

## Run the Eval

```bash
# Run inside container (recommended)
docker compose exec web python -m scripts.eval.run_eval --input scripts/eval/smoke2.jsonl --out scripts/eval/reports/reviews/$(date +%Y%m%d-%H%M%S)
```

Environment (choose one profile):

- Local (Ollama):
  - `LLM_API_BASE_URL=http://host.docker.internal:11434/v1`
  - `LLM_MODEL=llama3.1:8b`
- Runpod (vLLM):
  - `LLM_API_BASE_URL=http(s)://<runpod-host>:<port>/v1`
  - `LLM_MODEL=<llama-3.1-70b-instruct-awq>`

Optional tuning:
- `LLM_TEMPERATURE` (default 0.2)
- `LLM_TOP_P` (default 0.9)
- `LLM_MAX_TOKENS` (default 256)
- `LLM_TIMEOUT` (default 600)
- `LLM_CONCURRENCY` (default 1)

## Outputs

Artifacts are written to `scripts/eval/reports/`:
- `predictions.jsonl` and `predictions.csv`: model outputs per song
- `summary.json`: aggregate metrics
- `report.html`: quick human-readable summary
- `gpt_review_inputs.json/.jsonl/.csv`: inputs prepared for external LLM review

## Notes

- The eval harness is router-only (OpenAI-compatible HTTP). The legacy `--local` path is ignored.
- Ensure the base URL is reachable (`GET $LLM_API_BASE_URL/models`).
- Use `LLM_CONCURRENCY` to control parallel requests.
