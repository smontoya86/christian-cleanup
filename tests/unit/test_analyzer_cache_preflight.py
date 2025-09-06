import os
from types import SimpleNamespace

import pytest

from app.services.analyzer_cache import AnalyzerCache, clear_analyzer_cache


class DummyResp:
    def __init__(self, status_code=200, json_data=None, headers=None):
        self.status_code = status_code
        self._json = json_data or {}
        self.headers = headers or {"content-type": "application/json"}

    def json(self):
        return self._json


@pytest.fixture(autouse=True)
def reset_cache_env(monkeypatch):
    # Ensure a clean environment and cache for each test
    for k in [
        "LLM_API_BASE_URL",
    ]:
        if k in os.environ:
            monkeypatch.delenv(k, raising=False)
    clear_analyzer_cache()
    yield
    clear_analyzer_cache()


def _mock_get_factory(available_url: str):
    def _mock_get(url, timeout=1.5, *args, **kwargs):
        if url.startswith(f"{available_url.rstrip('/')}/models"):
            # Return a vLLM-like models payload
            return DummyResp(
                200,
                json_data={"data": [{"id": os.environ.get("LLM_MODEL", "stub-model")} ]},
            )
        # Simulate unreachable endpoints
        raise Exception("unreachable")

    return _mock_get


def test_detection_prefers_vllm_over_ollama(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "stub-model")
    # Simulate only vLLM being reachable
    mock_get = _mock_get_factory("http://llm:8000/v1")
    monkeypatch.setattr("app.services.analyzer_cache.requests.get", mock_get)

    cache = AnalyzerCache()
    analyzer = cache.get_analyzer()
    assert analyzer is not None
    # Should set base to vLLM
    assert os.environ.get("LLM_API_BASE_URL") == "http://llm:8000/v1"
    info = cache.get_model_info()
    assert info.get("endpoint") == "http://llm:8000/v1"


def test_detection_falls_back_to_ollama(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "stub-model")

    def mock_get(url, timeout=1.5, *args, **kwargs):
        if url.startswith("http://ollama:11434/v1/models"):
            return DummyResp(200, json_data=[{"name": "stub-model"}])
        # All other candidates unreachable
        raise Exception("unreachable")

    monkeypatch.setattr("app.services.analyzer_cache.requests.get", mock_get)

    cache = AnalyzerCache()
    _ = cache.get_analyzer()
    assert os.environ.get("LLM_API_BASE_URL") == "http://ollama:11434/v1"


def test_preflight_reports_not_enabled_when_nothing_reachable(monkeypatch):
    # No endpoints available
    def mock_get(*args, **kwargs):
        raise Exception("unreachable")

    monkeypatch.setattr("app.services.analyzer_cache.requests.get", mock_get)
    cache = AnalyzerCache()
    ok, msg = cache.preflight()
    assert ok is True
    assert "not enabled" in msg.lower()


