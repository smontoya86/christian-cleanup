"""
Analyzer provider resolver

Defaults to router; HF disabled regardless of legacy flags.

Env:
- ANALYZER_PROVIDER=router (default)
- USE_HF_ANALYZER (ignored)
"""

import os
from typing import Any

from app.services.analyzers import RouterAnalyzer


def get_analyzer() -> Any:
    provider = (os.environ.get("ANALYZER_PROVIDER") or "router").strip().lower()
    # Explicitly ignore any legacy HF flags
    if provider in ("router", "default", "openai", "llm"):
        return RouterAnalyzer()
    # Fallback to router for unknown values
    return RouterAnalyzer()


