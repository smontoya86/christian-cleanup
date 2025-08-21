"""
Calibration service stubs for testing compatibility.
These classes are referenced in tests via patching; minimal definitions ensure importability.
"""

from typing import Any, Dict, List


class ScoreDistributionAnalyzer:
    def analyze_distribution(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {}


class ThresholdOptimizer:
    def optimize_thresholds(self, *args, **kwargs) -> Dict[str, Any]:
        return {}


class PerformanceValidator:
    def compare_performance(self, *args, **kwargs) -> Dict[str, Any]:
        return {}


class SystemStabilityMonitor:
    def test_load_handling(self, *args, **kwargs) -> Dict[str, Any]:
        return {}


class CalibrationConfigManager:
    def load_config(self) -> Dict[str, Any]:
        return {}

    def save_config(self, config: Dict[str, Any]) -> bool:
        return True

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {"valid": True, "errors": []}


class CalibrationReporter:
    def generate_calibration_report(self) -> Dict[str, Any]:
        return {}

    def export_report(self, report: Dict[str, Any]) -> str:
        return "calibration_report.json"
