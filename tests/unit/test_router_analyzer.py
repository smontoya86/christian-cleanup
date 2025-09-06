import json
from unittest.mock import patch, Mock

import pytest

from app.services.analyzers.router_analyzer import RouterAnalyzer


class TestRouterAnalyzer:
    @patch("app.services.analyzers.router_analyzer.requests.post")
    def test_analyze_song_success_openai_style(self, mock_post):
        content = json.dumps({
            "score": 77,
            "concern_level": "Low",
            "biblical_themes": [{"theme": "Worship", "confidence": 0.9}],
            "supporting_scripture": [{"reference": "John 3:16"}],
            "concerns": [],
            "verdict": {"summary": "freely_listen"}
        })
        mock_resp = Mock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": content}}]}
        mock_resp.raise_for_status = Mock()
        mock_post.return_value = mock_resp

        ra = RouterAnalyzer()
        out = ra.analyze_song("Amazing Grace", "Traditional", "Amazing grace how sweet the sound")
        assert isinstance(out, dict)
        assert "score" in out and "concern_level" in out and "verdict" in out

    @patch("app.services.analyzers.router_analyzer.requests.post")
    def test_analyze_song_timeout_returns_default(self, mock_post):
        mock_post.side_effect = Exception("timeout")
        ra = RouterAnalyzer()
        out = ra.analyze_song("Title", "Artist", "Lyrics")
        assert out.get("score") == 50
        assert out.get("concern_level") == "Unknown"

    @patch("app.services.analyzers.router_analyzer.requests.post")
    def test_analyze_song_invalid_json_returns_default_shape(self, mock_post):
        mock_resp = Mock()
        # Not OpenAI-style and not dict with our fields -> default normalization
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = Mock()
        mock_post.return_value = mock_resp

        ra = RouterAnalyzer()
        out = ra.analyze_song("T", "A", "L")
        # ensure required fields exist
        for k in [
            "score",
            "concern_level",
            "biblical_themes",
            "supporting_scripture",
            "concerns",
            "verdict",
        ]:
            assert k in out


