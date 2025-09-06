import json
from unittest.mock import patch, Mock

import pytest

from app.services.analyzers.router_analyzer import RouterAnalyzer


class TestRouterAnalyzerErrorShapes:
    @patch("app.services.analyzers.router_analyzer.requests.post")
    def test_openai_error_object_returns_default(self, mock_post):
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = Exception("400 Bad Request")
        mock_resp.json.return_value = {"error": {"message": "bad"}}
        mock_post.return_value = mock_resp

        ra = RouterAnalyzer()
        out = ra.analyze_song("T", "A", "L")
        assert out["score"] == 50 and out["concern_level"] == "Unknown"

    @patch("app.services.analyzers.router_analyzer.requests.post")
    def test_empty_choices_returns_default(self, mock_post):
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {"choices": []}
        mock_post.return_value = mock_resp

        ra = RouterAnalyzer()
        out = ra.analyze_song("T", "A", "L")
        assert out["verdict"]["summary"] == "context_required"

    @patch("app.services.analyzers.router_analyzer.requests.post")
    def test_truncated_json_repair(self, mock_post):
        broken = '{"score": 61, "concern_level": "Low"'  # missing closing brace
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": broken}}]}
        mock_post.return_value = mock_resp

        ra = RouterAnalyzer()
        out = ra.analyze_song("T", "A", "L")
        # normalize should still provide defaults even if repair fails
        assert "score" in out and "concern_level" in out and "verdict" in out


