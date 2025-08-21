"""
Simplified Christian Analysis Service Tests

Tests for the new SimplifiedChristianAnalysisService that consolidates
the over-engineered analysis system while maintaining AI capabilities
and educational value for Christian discernment training.
"""

from unittest.mock import patch

import pytest

from app.services.simplified_christian_analysis_service import SimplifiedChristianAnalysisService
from app.utils.analysis.analysis_result import AnalysisResult


class TestSimplifiedChristianAnalysisService:
    """Test the simplified analysis service maintains quality while reducing complexity."""

    @pytest.fixture
    def service(self):
        """Create simplified analysis service for testing."""
        return SimplifiedChristianAnalysisService()

    @pytest.fixture
    def sample_christian_song(self):
        """Sample song with clear Christian themes."""
        return {
            "title": "Amazing Grace",
            "artist": "Chris Tomlin",
            "lyrics": """Amazing grace how sweet the sound
                         That saved a wretch like me
                         I once was lost but now am found
                         Was blind but now I see
                         Jesus Christ my savior Lord""",
        }

    @pytest.fixture
    def sample_concerning_song(self):
        """Sample song with concerning content."""
        return {
            "title": "Dark Temptations",
            "artist": "Test Artist",
            "lyrics": """Life is meaningless and dark
                         Nothing matters in this world
                         Hate and violence everywhere
                         God damn this broken life""",
        }

    @pytest.fixture
    def sample_nuanced_song(self):
        """Sample song requiring nuanced analysis."""
        return {
            "title": "Questioning Faith",
            "artist": "Deeper Artist",
            "lyrics": """Sometimes I wonder where you are
                         In the silence of my prayers
                         Though I cannot see your face
                         I choose to trust in your embrace
                         Even when the storms arise""",
        }

    def test_service_initialization(self, service):
        """Test that the service initializes correctly."""
        assert service is not None
        assert hasattr(service, "ai_analyzer"), "Should have AI analyzer component"
        assert hasattr(service, "scripture_mapper"), "Should have scripture mapping component"

    def test_christian_content_analysis_quality(self, service, sample_christian_song):
        """Test that Christian content receives appropriate scoring."""
        with patch.object(service, "ai_analyzer") as mock_ai:
            # Mock AI analysis with positive Christian results
            mock_ai.analyze_comprehensive.return_value = {
                "sentiment": {"label": "POSITIVE", "score": 0.95, "confidence": 0.92},
                "themes": ["salvation", "grace", "redemption", "divine love"],
                "content_safety": {"is_safe": True, "toxicity_score": 0.02},
                "emotions": ["joy", "peace", "reverence"],
                "theological_depth": 0.85,
            }

            result = service.analyze_song(
                sample_christian_song["title"],
                sample_christian_song["artist"],
                sample_christian_song["lyrics"],
            )

            # Quality requirements for Christian content
            assert (
                result.scoring_results["final_score"] >= 70
            ), "Strong Christian content should score 70+"
            assert (
                len(result.biblical_analysis["themes"]) >= 3
            ), "Should identify multiple Christian themes"
            assert result.scoring_results["quality_level"] in [
                "Very Low",
                "Low",
            ], "Should have minimal concerns"
            assert (
                "supporting_scripture" in result.biblical_analysis
            ), "Should provide scripture references"

    def test_concerning_content_proper_flagging(self, service, sample_concerning_song):
        """Test that concerning content is properly flagged with low scores."""
        with patch.object(service, "ai_analyzer") as mock_ai:
            # Mock AI analysis detecting concerning content
            mock_ai.analyze_comprehensive.return_value = {
                "sentiment": {"label": "NEGATIVE", "score": 0.89, "confidence": 0.91},
                "themes": ["despair", "nihilism", "profanity"],
                "content_safety": {"is_safe": False, "toxicity_score": 0.82},
                "emotions": ["anger", "hopelessness", "rage"],
                "theological_depth": 0.15,
            }

            result = service.analyze_song(
                sample_concerning_song["title"],
                sample_concerning_song["artist"],
                sample_concerning_song["lyrics"],
            )

            # Fixed expectations based on baseline findings
            assert (
                result.scoring_results["final_score"] <= 40
            ), "Concerning content should score ≤40"
            assert (
                len(result.content_analysis["concern_flags"]) >= 1
            ), "Should flag concerning elements"
            assert (
                result.scoring_results["quality_level"] == "High"
            ), "Should have high concern level"

    def test_nuanced_content_handling(self, service, sample_nuanced_song):
        """Test that nuanced content (spiritual questioning) gets moderate scores."""
        with patch.object(service, "ai_analyzer") as mock_ai:
            # Mock AI detecting spiritual questioning with appropriate nuance
            mock_ai.analyze_comprehensive.return_value = {
                "sentiment": {"label": "MIXED", "score": 0.65, "confidence": 0.73},
                "themes": ["spiritual searching", "faith questioning", "hope"],
                "content_safety": {"is_safe": True, "toxicity_score": 0.05},
                "emotions": ["contemplation", "uncertainty", "hope"],
                "theological_depth": 0.68,
            }

            result = service.analyze_song(
                sample_nuanced_song["title"],
                sample_nuanced_song["artist"],
                sample_nuanced_song["lyrics"],
            )

            # Fixed expectations for nuanced content
            assert (
                40 <= result.scoring_results["final_score"] <= 80
            ), "Nuanced content should score 40-80"
            assert result.scoring_results["quality_level"] in [
                "Low",
                "Medium",
            ], "Should have moderate concern"
            assert len(result.biblical_analysis["themes"]) >= 1, "Should recognize spiritual themes"

    def test_educational_value_requirements(self, service, sample_christian_song):
        """Test that analysis provides educational value for discernment training."""
        with (
            patch.object(service, "ai_analyzer") as mock_ai,
            patch.object(service, "scripture_mapper") as mock_scripture,
        ):
            # Mock comprehensive AI analysis
            mock_ai.analyze_comprehensive.return_value = {
                "sentiment": {"label": "POSITIVE", "score": 0.95, "confidence": 0.92},
                "themes": ["grace", "salvation", "redemption"],
                "content_safety": {"is_safe": True, "toxicity_score": 0.02},
                "emotions": ["joy", "peace"],
                "theological_depth": 0.85,
                "educational_insights": [
                    "This song reflects the Christian doctrine of grace",
                    "The theme of being 'lost and found' parallels biblical salvation narratives",
                ],
            }

            # Mock scripture mapping
            mock_scripture.find_relevant_passages.return_value = [
                "Ephesians 2:8-9 - For by grace you have been saved through faith",
                "Luke 15:4-7 - The Parable of the Lost Sheep",
            ]

            result = service.analyze_song(
                sample_christian_song["title"],
                sample_christian_song["artist"],
                sample_christian_song["lyrics"],
            )

            # Educational requirements
            explanation = result.scoring_results.get("explanation", "")
            assert len(explanation) >= 100, "Explanation should be substantial (100+ chars)"

            educational_content = result.biblical_analysis.get("educational_insights", [])
            assert len(educational_content) >= 1, "Should provide educational insights"

            scripture_refs = result.biblical_analysis.get("supporting_scripture", [])
            assert len(scripture_refs) >= 1, "Should provide relevant scripture"

            # Check for Christian educational concepts
            combined_text = f"{explanation} {' '.join(educational_content)}".lower()
            christian_concepts = [
                "grace",
                "salvation",
                "biblical",
                "faith",
                "christian",
                "scripture",
            ]
            assert any(
                concept in combined_text for concept in christian_concepts
            ), "Should reference Christian educational concepts"

    def test_performance_improvement(self, service, sample_christian_song):
        """Test that simplified service performs better than baseline."""
        import time

        with (
            patch.object(service, "ai_analyzer") as mock_ai,
            patch.object(service, "scripture_mapper") as mock_scripture,
        ):
            # Mock fast AI response
            mock_ai.analyze_comprehensive.return_value = {
                "sentiment": {"label": "POSITIVE", "score": 0.95, "confidence": 0.92},
                "themes": ["grace", "salvation"],
                "content_safety": {"is_safe": True, "toxicity_score": 0.02},
                "emotions": ["joy", "peace"],
                "theological_depth": 0.85,
            }

            mock_scripture.find_relevant_passages.return_value = [
                "Ephesians 2:8-9 - For by grace you have been saved"
            ]

            start_time = time.time()
            result = service.analyze_song(
                sample_christian_song["title"],
                sample_christian_song["artist"],
                sample_christian_song["lyrics"],
            )
            end_time = time.time()

            analysis_time = end_time - start_time

            # Performance requirements (should be faster than 2 second baseline)
            assert analysis_time <= 2.0, "Simplified analysis should complete within 2 seconds"
            assert result is not None, "Should successfully complete analysis"

    def test_simplified_architecture(self, service):
        """Test that the service uses simplified architecture."""
        # Should have only essential components
        essential_attributes = ["ai_analyzer", "scripture_mapper"]
        for attr in essential_attributes:
            assert hasattr(service, attr), f"Should have essential component: {attr}"

        # Should NOT have complex orchestration components
        unnecessary_attributes = ["orchestrator", "pattern_detector", "multiple_scorers"]
        for attr in unnecessary_attributes:
            assert not hasattr(service, attr), f"Should not have complex component: {attr}"

    def test_error_handling_robustness(self, service):
        """Test that the service handles errors gracefully."""
        with patch.object(service, "ai_analyzer") as mock_ai:
            # Simulate AI analyzer failure
            mock_ai.analyze_comprehensive.side_effect = Exception(
                "AI service temporarily unavailable"
            )

            result = service.analyze_song("Test Title", "Test Artist", "Test lyrics")

            # Should handle errors gracefully with fallback
            assert result is not None, "Should return result even on AI failure"
            assert hasattr(result, "scoring_results"), "Should have basic scoring structure"
            assert "explanation" in result.scoring_results, "Should provide fallback explanation"

    def test_ai_analyzer_integration(self, service):
        """Test that the service properly integrates with AI analyzer."""
        with patch.object(service, "ai_analyzer") as mock_ai:
            mock_ai.analyze_comprehensive.return_value = {
                "sentiment": {"label": "POSITIVE", "score": 0.85, "confidence": 0.80},
                "themes": ["hope", "encouragement"],
                "content_safety": {"is_safe": True, "toxicity_score": 0.05},
                "emotions": ["optimism"],
                "theological_depth": 0.65,
            }

            result = service.analyze_song("Test Title", "Test Artist", "Test lyrics")

            # Verify AI analyzer was called correctly
            mock_ai.analyze_comprehensive.assert_called_once()
            call_args = mock_ai.analyze_comprehensive.call_args[0]
            assert len(call_args) == 3, "Should pass title, artist, and lyrics"
            assert call_args[0] == "Test Title"
            assert call_args[1] == "Test Artist"
            assert call_args[2] == "Test lyrics"

    def test_scripture_mapping_integration(self, service):
        """Test that the service properly integrates with scripture mapping."""
        with (
            patch.object(service, "ai_analyzer") as mock_ai,
            patch.object(service, "scripture_mapper") as mock_scripture,
        ):
            mock_ai.analyze_comprehensive.return_value = {
                "sentiment": {"label": "POSITIVE", "score": 0.85, "confidence": 0.80},
                "themes": ["love", "forgiveness"],
                "content_safety": {"is_safe": True, "toxicity_score": 0.05},
                "emotions": ["peace"],
                "theological_depth": 0.70,
            }

            mock_scripture.find_relevant_passages.return_value = [
                "1 John 4:8 - God is love",
                "Matthew 6:14 - Forgive others",
            ]

            result = service.analyze_song("Test Title", "Test Artist", "Test lyrics")

            # Verify scripture mapper was called with themes
            mock_scripture.find_relevant_passages.assert_called_once()
            call_args = mock_scripture.find_relevant_passages.call_args[0]
            assert (
                "love" in call_args[0] or "forgiveness" in call_args[0]
            ), "Should pass detected themes"

    def test_result_structure_compatibility(self, service, sample_christian_song):
        """Test that results maintain compatibility with existing AnalysisResult structure."""
        with (
            patch.object(service, "ai_analyzer") as mock_ai,
            patch.object(service, "scripture_mapper") as mock_scripture,
        ):
            mock_ai.analyze_comprehensive.return_value = {
                "sentiment": {"label": "POSITIVE", "score": 0.95, "confidence": 0.92},
                "themes": ["grace", "salvation"],
                "content_safety": {"is_safe": True, "toxicity_score": 0.02},
                "emotions": ["joy"],
                "theological_depth": 0.85,
            }

            mock_scripture.find_relevant_passages.return_value = [
                "Ephesians 2:8-9 - Grace through faith"
            ]

            result = service.analyze_song(
                sample_christian_song["title"],
                sample_christian_song["artist"],
                sample_christian_song["lyrics"],
            )

            # Check required AnalysisResult structure
            assert isinstance(result, AnalysisResult), "Should return AnalysisResult instance"
            assert hasattr(result, "scoring_results"), "Should have scoring results"
            assert hasattr(result, "biblical_analysis"), "Should have biblical analysis"
            assert hasattr(result, "content_analysis"), "Should have content analysis"

            # Check required fields
            assert "final_score" in result.scoring_results, "Should have final score"
            assert "quality_level" in result.scoring_results, "Should have quality level"
            assert "explanation" in result.scoring_results, "Should have explanation"

            assert "themes" in result.biblical_analysis, "Should have biblical themes"
            assert "supporting_scripture" in result.biblical_analysis, "Should have scripture"
