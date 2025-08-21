#!/usr/bin/env python3
"""
Tests for Enhanced Scripture Mapper with Concern-Based Biblical Themes

Tests the enhanced scripture mapping functionality that provides biblical
foundation for both positive themes and concerning content detection.
"""

import os
import sys

import pytest

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.enhanced_scripture_mapper import EnhancedScriptureMapper


class TestEnhancedScriptureMapper:
    """Test the enhanced scripture mapper with concern-based themes."""

    @pytest.fixture
    def scripture_mapper(self):
        """Create scripture mapper instance for testing."""
        return EnhancedScriptureMapper()

    def test_initialization(self, scripture_mapper):
        """Test that scripture mapper initializes with both positive and concern themes."""
        # Should have existing positive themes
        assert "god" in scripture_mapper.scripture_database
        assert "jesus" in scripture_mapper.scripture_database
        assert "grace" in scripture_mapper.scripture_database

        # Should have new concern themes
        assert "concern_themes" in scripture_mapper.scripture_database
        concern_themes = scripture_mapper.scripture_database["concern_themes"]

        # Test all concern categories have biblical foundations
        expected_concern_themes = [
            "explicit_language",
            "sexual_content",
            "substance_abuse",
            "violence_aggression",
            "materialism_greed",
            "pride_arrogance",
            "occult_spiritual_darkness",
            "despair_hopelessness",
            "rebellion_authority",
            "false_teaching",
        ]

        for concern in expected_concern_themes:
            assert concern in concern_themes, f"Missing biblical foundation for {concern}"

    def test_concern_theme_structure(self, scripture_mapper):
        """Test that concern themes have proper structure with biblical foundation."""
        concern_themes = scripture_mapper.scripture_database["concern_themes"]

        # Test explicit_language theme structure
        explicit_theme = concern_themes["explicit_language"]
        assert "category" in explicit_theme
        assert "concern_addressed" in explicit_theme
        assert "scriptures" in explicit_theme
        assert len(explicit_theme["scriptures"]) > 0

        # Test scripture structure
        scripture = explicit_theme["scriptures"][0]
        required_fields = [
            "reference",
            "text",
            "teaching_point",
            "application",
            "contrast_principle",
        ]
        for field in required_fields:
            assert field in scripture, f"Missing {field} in scripture structure"

    def test_find_scriptural_foundation_for_concerns(self, scripture_mapper):
        """Test finding scriptural foundation for detected concerns."""
        # Mock detected concerns
        mock_concerns = [
            {"type": "explicit_language", "severity": "high"},
            {"type": "sexual_content", "severity": "high"},
            {"type": "materialism_greed", "severity": "medium"},
        ]

        result = scripture_mapper.find_scriptural_foundation_for_concerns(mock_concerns)

        # Should return scripture for each concern
        assert len(result) == 3

        # Each result should have proper structure
        for scripture_foundation in result:
            assert "concern_type" in scripture_foundation
            assert "biblical_theme" in scripture_foundation
            assert "scriptures" in scripture_foundation
            assert "teaching_summary" in scripture_foundation

    def test_get_comprehensive_scripture_references(self, scripture_mapper):
        """Test getting comprehensive scripture for both positive and concern themes."""
        positive_themes = ["worship", "grace", "love"]
        concern_themes = [
            {"concern_type": "explicit_language", "biblical_theme": "speech_purity"},
            {"concern_type": "pride_arrogance", "biblical_theme": "humility"},
        ]

        result = scripture_mapper.get_comprehensive_scripture_references(
            positive_themes, concern_themes
        )

        # Should have both positive and concern references
        assert "positive_references" in result
        assert "concern_references" in result
        assert "balanced_teaching" in result

        # Should have scripture for positive themes
        assert len(result["positive_references"]) > 0

        # Should have scripture for concern themes
        assert len(result["concern_references"]) > 0

        # Should provide balanced teaching
        assert len(result["balanced_teaching"]) > 0

    def test_sexual_content_biblical_foundation(self, scripture_mapper):
        """Test specific biblical foundation for sexual content concerns."""
        concern_themes = scripture_mapper.scripture_database["concern_themes"]
        sexual_theme = concern_themes["sexual_content"]

        # Should address sexual purity
        assert sexual_theme["concern_addressed"] == "sexual_content"
        assert "Purity" in sexual_theme["category"]

        # Should have relevant scripture
        scriptures = sexual_theme["scriptures"]
        assert len(scriptures) > 0

        # Should reference key purity passages
        references = [s["reference"] for s in scriptures]
        assert any("1 Corinthians 6" in ref for ref in references)

    def test_explicit_language_biblical_foundation(self, scripture_mapper):
        """Test specific biblical foundation for explicit language concerns."""
        concern_themes = scripture_mapper.scripture_database["concern_themes"]
        language_theme = concern_themes["explicit_language"]

        # Should address speech purity
        assert language_theme["concern_addressed"] == "explicit_language"
        assert "Communication" in language_theme["category"]

        # Should reference Ephesians 4:29
        scriptures = language_theme["scriptures"]
        references = [s["reference"] for s in scriptures]
        assert any("Ephesians 4:29" in ref for ref in references)

    def test_materialism_biblical_foundation(self, scripture_mapper):
        """Test biblical foundation for materialism and greed concerns."""
        concern_themes = scripture_mapper.scripture_database["concern_themes"]
        materialism_theme = concern_themes["materialism_greed"]

        # Should address materialism
        assert materialism_theme["concern_addressed"] == "materialism_greed"

        # Should reference key money/materialism passages
        scriptures = materialism_theme["scriptures"]
        references = [s["reference"] for s in scriptures]
        assert any("1 Timothy 6" in ref for ref in references)

    def test_violence_biblical_foundation(self, scripture_mapper):
        """Test biblical foundation for violence and aggression concerns."""
        concern_themes = scripture_mapper.scripture_database["concern_themes"]
        violence_theme = concern_themes["violence_aggression"]

        # Should address violence/aggression
        assert violence_theme["concern_addressed"] == "violence_aggression"

        # Should reference peace/nonviolence passages
        scriptures = violence_theme["scriptures"]
        references = [s["reference"] for s in scriptures]
        assert any("Matthew 5" in ref for ref in references)

    def test_occult_biblical_foundation(self, scripture_mapper):
        """Test biblical foundation for occult and spiritual darkness concerns."""
        concern_themes = scripture_mapper.scripture_database["concern_themes"]
        occult_theme = concern_themes["occult_spiritual_darkness"]

        # Should address occult practices
        assert occult_theme["concern_addressed"] == "occult_spiritual_darkness"

        # Should reference Deuteronomy 18 prohibition
        scriptures = occult_theme["scriptures"]
        references = [s["reference"] for s in scriptures]
        assert any("Deuteronomy 18" in ref for ref in references)

    def test_educational_content_quality(self, scripture_mapper):
        """Test that educational content maintains high quality and biblical accuracy."""
        concern_themes = scripture_mapper.scripture_database["concern_themes"]

        for theme_name, theme_data in concern_themes.items():
            # Each theme should have educational value
            assert "category" in theme_data
            assert len(theme_data["scriptures"]) > 0

            for scripture in theme_data["scriptures"]:
                # Teaching points should be substantial
                assert len(scripture["teaching_point"]) > 20
                # Applications should be practical
                assert len(scripture["application"]) > 20
                # Contrast principles should provide alternatives
                assert len(scripture["contrast_principle"]) > 10

    def test_backward_compatibility(self, scripture_mapper):
        """Test that existing positive theme functionality still works."""
        # Test existing methods still work
        positive_themes = ["god", "jesus", "worship", "grace"]
        result = scripture_mapper.find_relevant_passages(positive_themes)

        # Should still return scripture for positive themes
        assert len(result) > 0

        # Should maintain existing structure
        for passage in result:
            assert "reference" in passage
            assert "relevance" in passage


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
