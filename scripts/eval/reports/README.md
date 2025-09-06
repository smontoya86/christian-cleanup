# Reports directory layout

- predictions.csv / predictions.jsonl: Latest model outputs for the last run in the timestamped subfolder
- summary.json: Aggregated metrics for the last run in the timestamped subfolder
- report.html: Human-readable summary for the last run in the timestamped subfolder
- reviews/: Timestamped eval runs and DB exports

## Reviews folder

- reviews/<YYYYMMDD-HHMMSS>/
  - summary.json
  - predictions.csv
  - predictions.jsonl
  - gpt_review_inputs.json / .jsonl / .csv
  - report.html
  - meta.json (run metadata: timestamp, model, api_base, concurrency, etc.)
- reviews/db_gpt_review_inputs.*: Ground-truth exports from DB (no model_json)

Notes
-----
- Each eval run creates a new subfolder under `reviews/` with a timestamp and `meta.json`.
- Router-only: uses OpenAI-compatible HTTP (e.g., Ollama/vLLM). No local HF fallback.
- To run an eval and generate a new run folder:
  ```bash
  # default: Ollama at http://host.docker.internal:11434/v1, model llama3.1:8b
  bash scripts/eval/run_in_container.sh scripts/eval/english10.jsonl scripts/eval/reports
  ```
