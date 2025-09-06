import os
from unittest.mock import patch

from app.services.provider_resolver import get_analyzer
from app.services.analyzers.router_analyzer import RouterAnalyzer


def test_default_provider_is_router(monkeypatch):
    monkeypatch.delenv("ANALYZER_PROVIDER", raising=False)
    a = get_analyzer()
    assert isinstance(a, RouterAnalyzer)


def test_env_provider_router(monkeypatch):
    monkeypatch.setenv("ANALYZER_PROVIDER", "router")
    a = get_analyzer()
    assert isinstance(a, RouterAnalyzer)


def test_env_provider_invalid_falls_back_to_router(monkeypatch):
    monkeypatch.setenv("ANALYZER_PROVIDER", "huggingface")
    a = get_analyzer()
    assert isinstance(a, RouterAnalyzer)


