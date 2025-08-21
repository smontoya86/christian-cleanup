import json

import pytest


class DummyResp:
    def __init__(self, content_json):
        self._content_json = content_json

    def json(self):
        return {"choices": [{"message": {"content": self._content_json}}]}

    def raise_for_status(self):
        return None


@pytest.fixture
def mock_bible(monkeypatch):
    from app.utils.scripture.bsb_client import BsbClient

    def fake_fetch(self, reference: str):
        return {"reference": reference, "text": f"Text for {reference}"}

    monkeypatch.setattr(BsbClient, "fetch", fake_fetch)


def test_llm_analyzer_parses_valid_json(monkeypatch, mock_bible):
    # Arrange: mock the OpenAI-compatible endpoint
    valid = {
        "score": 92,
        "concern_level": "Very Low",
        "biblical_themes": [{"theme": "Gospel Presentation", "confidence": 0.91}],
        "supporting_scripture": [{"reference": "John 3:16", "theme": "Gospel Presentation"}],
        "concerns": [],
        "verdict": {"summary": "Gospel-rich", "guidance": "Safe for repeated listening"},
    }

    def fake_post(url, headers=None, data=None, timeout=None):
        return DummyResp(json.dumps(valid))

    monkeypatch.setenv("USE_LLM_ANALYZER", "1")
    monkeypatch.setenv("LLM_API_BASE_URL", "http://127.0.0.1:8080/v1")
    monkeypatch.setenv("LLM_MODEL", "mlx-community/Meta-Llama-3.1-8B-Instruct-4bit")

    import requests

    monkeypatch.setattr(requests, "post", fake_post)

    # Act
    from app.utils.analysis.llm_analyzer import LLMAnalyzer

    analyzer = LLMAnalyzer()
    result = analyzer.analyze_song("Test Song", "Test Artist", "lyrics with jesus and grace ...")

    # Assert
    assert result.is_successful()
    assert result.scoring_results.get("final_score") == 92
    assert result.content_analysis.get("concern_level") == "Very Low"
    scriptures = result.biblical_analysis.get("supporting_scripture", [])
    assert scriptures and scriptures[0].get("text", "").startswith("Text for ")


def test_llm_analyzer_chunks_and_merges(monkeypatch, mock_bible):
    # Arrange: force chunking and return different partials
    monkeypatch.setenv("USE_LLM_ANALYZER", "1")
    monkeypatch.setenv("LLM_CHUNK_CHAR_LIMIT", "20")  # small to force multiple chunks

    partial1 = {
        "score": 80,
        "concern_level": "Low",
        "biblical_themes": [{"theme": "Worship of God", "confidence": 0.6}],
        "supporting_scripture": [],
        "concerns": [],
        "verdict": {"summary": "Worshipful"},
    }
    partial2 = {
        "score": 60,
        "concern_level": "High",
        "biblical_themes": [{"theme": "Redemption", "confidence": 0.8}],
        "supporting_scripture": [],
        "concerns": [{"category": "Profanity", "severity": "high", "explanation": "obscene"}],
        "verdict": {"summary": "Some concerns"},
    }
    calls = {"n": 0}

    def fake_post(url, headers=None, data=None, timeout=None):
        payload = json.loads(data)
        # Alternate responses per chunk call
        if calls["n"] % 2 == 0:
            resp = DummyResp(json.dumps(partial1))
        else:
            resp = DummyResp(json.dumps(partial2))
        calls["n"] += 1
        return resp

    import requests

    monkeypatch.setattr(requests, "post", fake_post)

    from app.utils.analysis.llm_analyzer import LLMAnalyzer

    analyzer = LLMAnalyzer()
    long_lyrics = "line one jesus\nline two redemption\nthis includes profanity term"
    result = analyzer.analyze_song("Test Song", "Test Artist", long_lyrics)

    # Assert: merged should have worst concern level and union of themes
    assert result.is_successful()
    assert result.content_analysis.get("concern_level") in {"High", "Critical"}
    themes = [t.get("theme") for t in result.biblical_analysis.get("themes", [])]
    assert "Worship of God" in themes and "Redemption" in themes
    flags = result.get_content_flags()
    assert any(f.get("type") == "Profanity" for f in flags)
