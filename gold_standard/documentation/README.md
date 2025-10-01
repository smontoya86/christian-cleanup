Eval Harness
============

Overview
--------
This harness evaluates model outputs against labeled songs using an OpenAI-compatible endpoint (local or Runpod).

Files
-----
- songs_eval.example.jsonl: Schema template for labeled songs
- run_eval.py: Async runner that batches requests, validates JSON, computes metrics, and writes reports
- reports/: Output CSV/HTML artifacts

Usage
-----
1. Copy songs_eval.example.jsonl to songs_eval.jsonl and populate with your labeled set.
2. Set environment (Router-only):
   - LLM_API_BASE_URL=http://localhost:11434/v1  # Ollama local, or Runpod endpoint
   - LLM_MODEL=llama3.1:8b
3. Run: python scripts/eval/run_eval.py --input scripts/eval/songs_eval.jsonl --out scripts/eval/reports

Metrics
-------
- Verdict: accuracy, macro-F1
- Score: Pearson/Spearman, MAE
- Concern flags: micro/macro F1
- Scripture refs: Jaccard
- Latency: p50/p90/p99

Endpoint Switching
------------------
The runner reads LLM_API_BASE_URL and LLM_MODEL. Point it at local (Ollama/llama.cpp) or Runpod (vLLM) without code changes.

