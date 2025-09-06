#!/usr/bin/env bash
set -euo pipefail

# vLLM + Qwen2.5-14B-Instruct (AWQ 4-bit) startup for Runpod (BULK instance)
# Exposes OpenAI-compatible API at :8001/v1

MODEL="Qwen/Qwen2.5-14B-Instruct-AWQ"
PORT="8001"

docker run --gpus all --rm -p ${PORT}:8000 \
  -e VLLM_WORKER_USE_FP8=False \
  vllm/vllm-openai:latest \
  --model ${MODEL} \
  --quantization awq \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.90 \
  --max-num-seqs 512 \
  --tensor-parallel-size 1 \
  --trust-remote-code \
  --dtype auto \
  --port 8000

echo "Bulk vLLM started on port ${PORT}. OpenAI-compatible base: http://localhost:${PORT}/v1"

