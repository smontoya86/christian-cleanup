import pytest

from app.services.unified_analysis_service import UnifiedAnalysisService


class TestConcernLevelNormalization:
    def setup_method(self):
        self.svc = UnifiedAnalysisService()

    @pytest.mark.parametrize(
        "quality, expected",
        [
            ("High", "High"),
            ("Medium", "Medium"),
            ("Low", "Low"),
            ("Very Low", "Low"),  # map to allowed set
            ("Unknown", "Low"),   # conservative default
            ("", "Low"),
            (None, "Low"),
        ],
    )
    def test_map_concern_level_allowed_values(self, quality, expected):
        out = self.svc._map_concern_level(quality)
        assert out in {"Low", "Medium", "High"}
        assert out == expected


