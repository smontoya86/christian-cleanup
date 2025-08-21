"""
Analysis Result

Standardized data structure for analysis results.
Provides comprehensive output format for song analysis.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """
    Comprehensive analysis result data structure.

    Contains all analysis components including content detection,
    biblical themes, scoring, and metadata.
    """

    title: str
    artist: str
    lyrics_text: Optional[str] = None
    processed_text: Optional[str] = None

    # Analysis components
    content_analysis: Dict[str, Any] = field(default_factory=dict)
    biblical_analysis: Dict[str, Any] = field(default_factory=dict)
    model_analysis: Dict[str, Any] = field(default_factory=dict)
    scoring_results: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: Optional[int] = None
    analysis_version: str = "2.0"
    error_message: Optional[str] = None

    # Configuration snapshot
    configuration_snapshot: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create_error(
        cls, title: str, artist: str, error_message: str, **kwargs
    ) -> "AnalysisResult":
        """
        Create an error result.

        Args:
            title: Song title
            artist: Artist name
            error_message: Error description
            **kwargs: Additional metadata

        Returns:
            AnalysisResult with error information
        """
        return cls(title=title, artist=artist, error_message=error_message, **kwargs)

    def is_successful(self) -> bool:
        """
        Check if analysis was successful.

        Returns:
            True if successful, False if there were errors
        """
        return self.error_message is None

    def get_final_score(self) -> float:
        """
        Get the final analysis score.

        Returns:
            Final score (0-100) or 0 if error
        """
        if not self.is_successful():
            return 0.0

        return self.scoring_results.get("final_score", 0.0)

    def get_quality_level(self) -> str:
        """
        Get the quality assessment.

        Returns:
            Quality level string
        """
        if not self.is_successful():
            return "error"

        return self.scoring_results.get("quality_level", "unknown")

    def get_content_flags(self) -> List[Dict[str, Any]]:
        """
        Get list of content flags detected.

        Returns:
            List of content flag dictionaries
        """
        if not self.is_successful():
            return []

        # Check for HuggingFace analyzer format first (concern_flags list)
        concern_flags = self.content_analysis.get("concern_flags", [])
        if concern_flags:
            return concern_flags

        # Fallback to legacy format
        flags = []
        for filter_type, results in self.content_analysis.items():
            if filter_type in ["total_penalty", "concern_flags", "safety_assessment"]:
                continue

            if isinstance(results, dict) and results.get("detected", False):
                flags.append(
                    {
                        "type": filter_type,
                        "confidence": results.get("confidence", 0.0),
                        "details": results.get("details", []),
                    }
                )

        return flags

    def get_biblical_themes(self) -> List[Dict[str, Any]]:
        """
        Get list of detected biblical themes.

        Returns:
            List of theme dictionaries
        """
        if not self.is_successful():
            return []

        return self.biblical_analysis.get("themes", [])

    def get_component_scores(self) -> Dict[str, float]:
        """
        Get individual component scores.

        Returns:
            Dictionary of component scores
        """
        if not self.is_successful():
            return {}

        return self.scoring_results.get("component_scores", {})

    def get_summary(self) -> Dict[str, Any]:
        """
        Get concise analysis summary.

        Returns:
            Summary dictionary with key metrics
        """
        summary = {
            "title": self.title,
            "artist": self.artist,
            "timestamp": self.timestamp.isoformat(),
            "processing_time": self.processing_time,
            "success": self.is_successful(),
        }

        if self.is_successful():
            summary.update(
                {
                    "final_score": self.get_final_score(),
                    "quality_level": self.get_quality_level(),
                    "content_flags_count": len(self.get_content_flags()),
                    "biblical_themes_count": len(self.get_biblical_themes()),
                    "total_penalty": self.scoring_results.get("total_penalty", 0),
                    "total_bonus": self.scoring_results.get("total_bonus", 0),
                }
            )
        else:
            summary["error"] = self.error_message

        return summary

    def get_recommendation(self) -> str:
        """
        Get recommendation based on analysis.

        Returns:
            Recommendation string
        """
        if not self.is_successful():
            return "Unable to analyze - please try again"

        score = self.get_final_score()

        if score >= 85:
            return "Highly recommended for Christian audiences"
        elif score >= 70:
            return "Generally appropriate for Christian audiences"
        elif score >= 50:
            return "Review recommended - some concerns may apply"
        else:
            return "Not recommended for Christian audiences"
