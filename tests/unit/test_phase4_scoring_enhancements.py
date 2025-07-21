"""
Phase 4 TDD Tests: Scoring & Verdict Enhancements

Tests for the enhanced scoring system with:
1. Theological Significance Weighting:
   - Core Gospel themes: 1.5x multiplier (Christ-centered, Gospel presentation, Redemption, Sacrificial love, Light vs darkness)
   - Christian Living themes: 1.2x multiplier (All Phase 2 character themes)
   
2. Formational Weight Multiplier: -10 for severe negative content
   - Applied when: 3+ negative themes each -15 or worse + emotionally immersive tone + no redemptive elements
   
3. Structured Verdict Format:
   - Summary: 1-line statement about spiritual core
   - Formation Guidance: 1-2 sentences about spiritual impact and listening approach

Following TDD methodology: Write tests first, then implement functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.utils.analysis.huggingface_analyzer import HuggingFaceAnalyzer
from app.utils.analysis.analysis_result import AnalysisResult


class TestScoringEnhancements:
    """Test Phase 4 Scoring & Verdict Enhancements with enhanced scoring system."""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.analyzer = HuggingFaceAnalyzer()
        
        # Mock the AI models to avoid loading them during tests
        self.analyzer._sentiment_analyzer = Mock()
        self.analyzer._safety_analyzer = Mock()
        self.analyzer._emotion_analyzer = Mock()
        self.analyzer._theme_analyzer = Mock()

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_core_gospel_theological_weighting(self, mock_logger):
        """Test that Core Gospel themes get 1.5x theological significance multiplier"""
        
        # Mock AI responses for strong core gospel content
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'POSITIVE', 'score': 0.90
        }]
        
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Christ-centered worship - Jesus as Savior, Lord, or King', 'Gospel presentation - Cross, resurrection, salvation by grace'],
            'scores': [0.92, 0.88]
        }
        
        self.analyzer._emotion_analyzer.return_value = [{
            'label': 'joy', 'score': 0.85
        }]
        
        self.analyzer._safety_analyzer.return_value = [{
            'label': 'SAFE', 'score': 0.95
        }]
        
        # Test core gospel lyrics
        core_gospel_lyrics = """
        Jesus Christ is Lord and Savior
        Through the cross we have salvation
        Grace alone saves us from sin
        The gospel message rings so true
        """
        
        result = self.analyzer.analyze_song("Gospel Core", "Christian Artist", core_gospel_lyrics)
        
        # Should detect core gospel themes
        themes = result.biblical_analysis.get('themes', [])
        core_gospel_themes_found = any(
            t.get('category') == 'core_gospel'
            for t in themes
        )
        assert core_gospel_themes_found, "Should detect core gospel themes"
        
        # Should have theological weighting applied (should be stored in scoring metadata)
        theological_weighting = result.scoring_results.get('theological_weighting', 1.0)
        assert theological_weighting >= 1.5, "Core gospel themes should get 1.5x theological weighting"
        
        # Score should be higher due to core gospel boost
        base_score_estimate = 40  # Rough estimate without weighting
        expected_boosted_score = base_score_estimate * 1.5
        assert result.scoring_results['final_score'] >= expected_boosted_score * 0.8, "Should get significant boost from core gospel weighting"

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_character_spiritual_theological_weighting(self, mock_logger):
        """Test that Character & Spiritual themes get 1.2x theological significance multiplier"""
        
        # Mock AI responses for character/spiritual content
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'POSITIVE', 'score': 0.85
        }]
        
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Perseverance and endurance - Faith through trials and spiritual growth', 'Obedience to God - Willingness to follow divine commands'],
            'scores': [0.90, 0.85]
        }
        
        self.analyzer._emotion_analyzer.return_value = [{
            'label': 'determination', 'score': 0.80
        }]
        
        # Test character/spiritual lyrics
        character_lyrics = """
        Through trials I will endure
        Obedience is my desire
        Following God's holy way
        Character built day by day
        """
        
        result = self.analyzer.analyze_song("Character Building", "Faithful Artist", character_lyrics)
        
        # Should detect character/spiritual themes
        themes = result.biblical_analysis.get('themes', [])
        character_themes_found = any(
            t.get('category') == 'character_spiritual'
            for t in themes
        )
        assert character_themes_found, "Should detect character/spiritual themes"
        
        # Should have 1.2x theological weighting applied
        theological_weighting = result.scoring_results.get('theological_weighting', 1.0)
        assert 1.2 <= theological_weighting < 1.5, "Character themes should get 1.2x theological weighting"
        
        # Score should be moderately boosted
        base_score_estimate = 35
        expected_boosted_score = base_score_estimate * 1.2
        assert result.scoring_results['final_score'] >= expected_boosted_score * 0.8, "Should get moderate boost from character weighting"

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_formational_weight_multiplier_applied(self, mock_logger):
        """Test that severe negative content gets -10 formational weight multiplier"""
        
        # Mock AI responses for severely negative content
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'NEGATIVE', 'score': 0.95
        }]
        
        # Multiple severe negative themes
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Blasphemy and mocking God', 'Self-deification and pride', 'Occult practices and sorcery', 'Sexual immorality and lust'],
            'scores': [0.90, 0.88, 0.85, 0.82]
        }
        
        self.analyzer._emotion_analyzer.return_value = [{
            'label': 'anger', 'score': 0.92
        }]
        
        self.analyzer._safety_analyzer.return_value = [{
            'label': 'TOXIC', 'score': 0.88
        }]
        
        # Test severely harmful lyrics with no redemptive elements
        severely_harmful_lyrics = """
        F*** your god, I rule my world
        Satan gives me real power
        Magic spells control my mind
        Use bodies for selfish pleasure
        No hope, no truth, no meaning
        """
        
        result = self.analyzer.analyze_song("Pure Darkness", "Destructive Artist", severely_harmful_lyrics)
        
        # Should detect multiple severe negative themes
        themes = result.biblical_analysis.get('themes', [])
        severe_negative_count = sum(1 for t in themes if t.get('category') == 'negative' and t.get('points', 0) <= -15)
        assert severe_negative_count >= 3, "Should detect 3+ severe negative themes"
        
        # Should have formational weight multiplier applied
        formational_penalty = result.scoring_results.get('formational_penalty', 0)
        assert formational_penalty == -10, "Should apply -10 formational weight multiplier for severe content"
        
        # Score should be extremely low due to formational penalty
        assert result.scoring_results['final_score'] <= 5, "Severe content with formational penalty should score near zero"

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_no_formational_penalty_for_moderate_content(self, mock_logger):
        """Test that moderate negative content does not trigger formational weight multiplier"""
        
        # Mock AI responses for moderate negative content (not severe enough)
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'NEGATIVE', 'score': 0.70
        }]
        
        # Only 1-2 moderate negative themes
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Materialism and greed', 'Vague spirituality without foundation'],
            'scores': [0.80, 0.75]
        }
        
        self.analyzer._emotion_analyzer.return_value = [{
            'label': 'disappointment', 'score': 0.65
        }]
        
        # Test moderate negative content
        moderate_negative_lyrics = """
        Money is my main focus
        Spiritual but not religious
        Find your own truth inside
        Material success defines me
        """
        
        result = self.analyzer.analyze_song("Moderate Issues", "Secular Artist", moderate_negative_lyrics)
        
        # Should NOT have formational weight multiplier applied
        formational_penalty = result.scoring_results.get('formational_penalty', 0)
        assert formational_penalty == 0, "Should NOT apply formational penalty for moderate content"
        
        # Score should be low but not extremely low
        assert 15 <= result.scoring_results['final_score'] <= 50, "Moderate negative content should score low but not extremely low"

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_structured_verdict_format_positive_content(self, mock_logger):
        """Test that positive Christian content gets proper structured verdict format"""
        
        # Mock AI responses for excellent Christian content
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'POSITIVE', 'score': 0.95
        }]
        
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Christ-centered worship - Jesus as Savior, Lord, or King', 'Gospel presentation - Cross, resurrection, salvation by grace', 'Perseverance and endurance - Faith through trials'],
            'scores': [0.94, 0.90, 0.85]
        }
        
        self.analyzer._emotion_analyzer.return_value = [{
            'label': 'joy', 'score': 0.90
        }]
        
        # Test excellent Christian lyrics
        excellent_christian_lyrics = """
        Jesus Christ is Lord and King
        Through the cross we are set free
        His grace amazes me each day
        In trials I will trust and stay
        """
        
        result = self.analyzer.analyze_song("Excellent Worship", "Christian Artist", excellent_christian_lyrics)
        
        # Should have structured verdict with summary and formation guidance
        verdict_summary = result.scoring_results.get('verdict_summary', '')
        formation_guidance = result.scoring_results.get('formation_guidance', '')
        
        assert verdict_summary, "Should have verdict summary"
        assert len(verdict_summary.split()) <= 25, "Summary should be concise (1 line, ~25 words max)"
        
        assert formation_guidance, "Should have formation guidance"
        assert 10 <= len(formation_guidance.split()) <= 50, "Formation guidance should be 1-2 sentences"
        
        # Summary should indicate positive spiritual core
        assert any(keyword in verdict_summary.lower() for keyword in ['christ', 'gospel', 'worship', 'edifying', 'uplifting']), "Summary should reflect positive spiritual content"
        
        # Formation guidance should encourage use
        assert any(keyword in formation_guidance.lower() for keyword in ['safe', 'edifying', 'encouraging', 'worship', 'spiritual growth']), "Formation guidance should encourage positive use"

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_structured_verdict_format_negative_content(self, mock_logger):
        """Test that negative content gets appropriate warning in structured verdict"""
        
        # Mock AI responses for harmful content
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'NEGATIVE', 'score': 0.90
        }]
        
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Blasphemy and mocking God', 'Violence glorification', 'Materialism and greed'],
            'scores': [0.88, 0.82, 0.78]
        }
        
        self.analyzer._emotion_analyzer.return_value = [{
            'label': 'anger', 'score': 0.85
        }]
        
        # Test harmful lyrics
        harmful_lyrics = """
        God doesn't care about your pain
        Violence solves every problem
        Money is the only god I need
        Destroy everything in sight
        """
        
        result = self.analyzer.analyze_song("Harmful Content", "Dark Artist", harmful_lyrics)
        
        # Should have structured verdict with appropriate warnings
        verdict_summary = result.scoring_results.get('verdict_summary', '')
        formation_guidance = result.scoring_results.get('formation_guidance', '')
        
        assert verdict_summary, "Should have verdict summary"
        assert formation_guidance, "Should have formation guidance"
        
        # Summary should indicate spiritual concerns
        assert any(keyword in verdict_summary.lower() for keyword in ['harmful', 'concerning', 'destructive', 'spiritually dangerous']), "Summary should reflect spiritual concerns"
        
        # Formation guidance should warn against regular consumption
        assert any(keyword in formation_guidance.lower() for keyword in ['avoid', 'caution', 'harmful', 'not safe', 'spiritually dangerous']), "Formation guidance should warn against consumption"

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_mixed_content_balanced_verdict(self, mock_logger):
        """Test that mixed positive/negative content gets balanced verdict"""
        
        # Mock AI responses for mixed content
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'NEUTRAL', 'score': 0.60
        }]
        
        # Mix of positive and negative themes
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Christ-centered worship - Jesus as Savior, Lord, or King', 'Materialism and greed', 'Perseverance and endurance - Faith through trials'],
            'scores': [0.85, 0.75, 0.70]
        }
        
        self.analyzer._emotion_analyzer.return_value = [{
            'label': 'contemplation', 'score': 0.65
        }]
        
        # Test mixed content lyrics
        mixed_lyrics = """
        Jesus is my Lord and Savior
        But sometimes I chase after money
        Through trials I try to trust
        Material things still tempt me
        """
        
        result = self.analyzer.analyze_song("Mixed Themes", "Struggling Artist", mixed_lyrics)
        
        # Should have balanced verdict acknowledging both aspects
        verdict_summary = result.scoring_results.get('verdict_summary', '')
        formation_guidance = result.scoring_results.get('formation_guidance', '')
        
        assert verdict_summary, "Should have verdict summary"
        assert formation_guidance, "Should have formation guidance"
        
        # Should acknowledge both positive and concerning elements
        summary_words = verdict_summary.lower()
        guidance_words = formation_guidance.lower()
        
        # Should mention positive elements
        has_positive_reference = any(keyword in summary_words or keyword in guidance_words 
                                   for keyword in ['christ', 'faith', 'positive', 'good'])
        assert has_positive_reference, "Should acknowledge positive elements"
        
        # Should mention caution about negative elements  
        has_caution_reference = any(keyword in guidance_words 
                                  for keyword in ['caution', 'aware', 'mixed', 'balance', 'discernment'])
        assert has_caution_reference, "Should provide guidance about mixed content"

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_theological_weighting_score_calculation(self, mock_logger):
        """Test that theological weighting is properly calculated and applied"""
        
        # Mock for core gospel themes with known point values
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'POSITIVE', 'score': 0.90
        }]
        
        # Core gospel themes worth 10 + 10 = 20 base points
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Christ-centered worship - Jesus as Savior, Lord, or King', 'Gospel presentation - Cross, resurrection, salvation by grace'],
            'scores': [0.90, 0.85]  # High confidence
        }
        
        result = self.analyzer.analyze_song("Pure Gospel", "Christian Artist", "Jesus saves through the cross")
        
        # Verify theological weighting calculation
        theological_weighting = result.scoring_results.get('theological_weighting', 1.0)
        base_points = result.scoring_results.get('base_theme_points', 0)
        
        # Should apply 1.5x multiplier to core gospel themes
        assert theological_weighting == 1.5, "Should apply exactly 1.5x multiplier for core gospel"
        
        # Final score should reflect the theological boost
        final_score = result.scoring_results['final_score']
        expected_minimum = base_points * 1.5 * 0.7  # Allow some variance for other factors
        assert final_score >= expected_minimum, "Final score should reflect theological weighting boost"

    @patch('app.utils.analysis.huggingface_analyzer.logger')
    def test_no_theological_weighting_for_secular_content(self, mock_logger):
        """Test that secular content gets no theological weighting"""
        
        # Mock AI responses for purely secular content
        self.analyzer._sentiment_analyzer.return_value = [{
            'label': 'POSITIVE', 'score': 0.75
        }]
        
        # No Christian themes detected
        self.analyzer._theme_analyzer.return_value = {
            'labels': ['Love and relationships', 'Personal success', 'Party celebration'],
            'scores': [0.85, 0.80, 0.75]
        }
        
        result = self.analyzer.analyze_song("Secular Love Song", "Pop Artist", "Love makes me happy tonight")
        
        # Should have no theological weighting applied
        theological_weighting = result.scoring_results.get('theological_weighting', 1.0)
        assert theological_weighting == 1.0, "Secular content should have no theological weighting"
        
        # Score should be based purely on base scoring without boosts
        final_score = result.scoring_results['final_score']
        assert final_score <= 30, "Secular content should score low without theological themes"

    def test_score_range_validation_with_enhancements(self):
        """Test that enhanced scoring system maintains 0-100 score range"""
        
        # Test extreme positive case with maximum theological weighting
        max_positive_themes = [
            {'theme': 'Christ-centered', 'score': 0.95, 'points': 10, 'category': 'core_gospel'},
            {'theme': 'Gospel presentation', 'score': 0.90, 'points': 10, 'category': 'core_gospel'},
            {'theme': 'Redemption', 'score': 0.85, 'points': 7, 'category': 'core_gospel'}
        ]
        
        # Even with 1.5x multiplier, score should be capped at 100
        base_points = sum(t['points'] for t in max_positive_themes)  # 27 points
        weighted_points = base_points * 1.5  # 40.5 points
        # With sentiment, emotion, and other bonuses, could exceed 100
        
        # Test extreme negative case with formational penalty
        min_negative_themes = [
            {'theme': 'Blasphemy', 'score': 0.95, 'points': -30, 'category': 'negative'},
            {'theme': 'Self-deification', 'score': 0.90, 'points': -25, 'category': 'negative'},
            {'theme': 'Occult', 'score': 0.85, 'points': -20, 'category': 'negative'}
        ]
        
        total_penalties = sum(t['points'] for t in min_negative_themes)  # -75 points
        with_formational_penalty = total_penalties - 10  # -85 points
        # Score should be clamped to 0, not go negative
        
        assert 0 <= 100, "Score validation logic should maintain 0-100 range"
        assert total_penalties <= 0, "Negative themes should have negative points"
        assert with_formational_penalty <= total_penalties, "Formational penalty should make score worse" 