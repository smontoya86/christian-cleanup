"""
LLM Provider Configuration

Simple configuration for LLM providers to avoid hardcoding in the router.
"""

import os

# LLM Provider Configurations
LLM_PROVIDERS = [
    {
        "name": "runpod",
        "endpoint": os.environ.get("RUNPOD_ENDPOINT"),
        "model": os.environ.get("RUNPOD_MODEL", "llama3.1:70b"),
        "priority": 1,
        "timeout": 15.0,
        "max_retries": 3,
        "api_key_env": "RUNPOD_API_KEY"
    },
    {
        "name": "ollama",
        "endpoint": os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434"),
        "model": os.environ.get("OLLAMA_MODEL", "llama3.1:8b"),
        "priority": 2,
        "timeout": 8.0,
        "max_retries": 2,
        "api_key_env": None  # Ollama doesn't require API key
    }
]

# Fallback endpoints for Ollama (in order of preference)
OLLAMA_FALLBACK_ENDPOINTS = [
    "http://ollama:11434",
    "http://localhost:11434", 
    "http://host.docker.internal:11434",
    "http://llm:8000"  # Current working endpoint
]
