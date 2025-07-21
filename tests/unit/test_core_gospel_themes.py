"""
Phase 1 TDD Tests: Core Gospel Themes Detection

Tests for the 5 core gospel themes:
- Christ-Centered: Jesus as Savior, Lord, or King (+10 points)
- Gospel Presentation: Cross, resurrection, salvation by grace (+10 points)  
- Redemption: Deliverance by grace (+7 points)
- Sacrificial Love: Christlike self-giving (+6 points)
- Light vs Darkness: Spiritual clarity and contrast (+5 points)

Following TDD methodology: Write tests first, then implement functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.utils.analysis.huggingface_analyzer import HuggingFaceAnalyzer
from app.utils.analysis.analysis_result import AnalysisResult


class TestCoreGospelThemes:
    """Test Core Gospel Themes detection with enhanced HuggingFace models."""
    
    @pytest.fixture
    def mock_hf_analyzer(self):
        """Create a mock HuggingFace analyzer for testing."""
        with patch('app.utils.analysis.huggingface_analyzer.pipeline'):
            analyzer = HuggingFaceAnalyzer()
            # Mock the models to avoid loading in tests
            analyzer._sentiment_analyzer = Mock()
            analyzer._safety_analyzer = Mock()
            analyzer._emotion_analyzer = Mock()
            analyzer._theme_analyzer = Mock()  # New zero-shot classifier
            return analyzer
    
    @pytest.fixture
    def christ_centered_song(self):
        """Test song with clear Christ-centered themes."""
        return {
            "title": "Jesus Is Lord",
            "artist": "Hillsong Worship",
            "lyrics": """Jesus Christ is Lord of all
                         King of kings and Lord of lords
                         Savior of the world, our Redeemer
                         Jesus is the way, the truth, the life
                         No one comes to the Father except through Him"""
        }
    
    @pytest.fixture
    def gospel_presentation_song(self):
        """Test song with clear gospel presentation."""
        return {
            "title": "The Cross",
            "artist": "Chris Tomlin", 
            "lyrics": """On the cross He died for me
                         Resurrection power set me free
                         Salvation by grace through faith alone
                         Not by works, but Christ atoned
                         He rose again on the third day"""
        }
    
    @pytest.fixture
    def redemption_song(self):
        """Test song with redemption themes."""
        return {
            "title": "Redeemed",
            "artist": "Big Daddy Weave",
            "lyrics": """I am redeemed by the blood of the Lamb
                         Grace has delivered me from sin's demand
                         Bought with a price, no longer slave
                         Redemption's song is what I'll sing"""
        }
    
    @pytest.fixture
    def sacrificial_love_song(self):
        """Test song with sacrificial love themes."""
        return {
            "title": "Greater Love",
            "artist": "Christian Artist",
            "lyrics": """Greater love has no one than this
                         To lay down one's life for friends
                         Jesus gave His all for us
                         Sacrificial love divine
                         Self-giving love of Christ"""
        }
    
    @pytest.fixture
    def light_vs_darkness_song(self):
        """Test song with light vs darkness spiritual themes."""
        return {
            "title": "Light in the Darkness",
            "artist": "Worship Leader",
            "lyrics": """The light shines in the darkness
                         And darkness cannot overcome
                         Jesus is the light of the world
                         Breaking chains of spiritual night
                         Victory over powers of darkness"""
        }
    
    @pytest.fixture
    def secular_song(self):
        """Test secular song that should NOT trigger gospel themes."""
        return {
            "title": "Party Tonight",
            "artist": "Pop Artist",
            "lyrics": """We're gonna party all night long
                         Dancing until the break of dawn
                         Living life without a care
                         Money, fame, and fortune everywhere"""
        }

    def test_christ_centered_detection_positive_cases(self, mock_hf_analyzer, christ_centered_song):
        """Test Christ-centered theme detection with high confidence."""
        # Mock zero-shot classification response for Christ-centered theme
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Christ-centered worship', 'score': 0.95},
            {'label': 'Jesus as Lord and Savior', 'score': 0.92},
            {'label': 'Divine kingship', 'score': 0.88}
        ]
        
        # Mock other analyzers for complete analysis
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.9}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.95}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'joy', 'score': 0.85}]
        
        result = mock_hf_analyzer.analyze_song(
            christ_centered_song["title"],
            christ_centered_song["artist"], 
            christ_centered_song["lyrics"]
        )
        
        # Expected: +10 points for Christ-centered theme
        assert result is not None
        assert isinstance(result, AnalysisResult)
        
        # Check that Christ-centered theme was detected
        themes = result.biblical_analysis.get('themes', [])
        christ_themes = [t for t in themes if 'christ' in t.get('theme', '').lower() or 'jesus' in t.get('theme', '').lower()]
        assert len(christ_themes) > 0, "Should detect Christ-centered themes"
        
        # Score should be high due to Christ-centered content (realistic expectation)
        assert result.scoring_results['final_score'] >= 70, "Christ-centered songs should score highly"

    def test_gospel_presentation_detection(self, mock_hf_analyzer, gospel_presentation_song):
        """Test gospel presentation theme detection."""
        # Mock zero-shot classification for gospel themes
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Gospel presentation', 'score': 0.93},
            {'label': 'Cross and resurrection', 'score': 0.91},
            {'label': 'Salvation by grace', 'score': 0.89}
        ]
        
        # Mock other analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.88}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.96}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'joy', 'score': 0.82}]
        
        result = mock_hf_analyzer.analyze_song(
            gospel_presentation_song["title"],
            gospel_presentation_song["artist"],
            gospel_presentation_song["lyrics"]
        )
        
        # Expected: +10 points for gospel presentation
        assert result is not None
        
        # Check for gospel-related themes
        themes = result.biblical_analysis.get('themes', [])
        gospel_keywords = ['cross', 'resurrection', 'salvation', 'grace', 'faith']
        gospel_themes_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in gospel_keywords) 
            for t in themes
        )
        assert gospel_themes_found, "Should detect gospel presentation themes"
        
        # Score should be high for clear gospel content (realistic expectation)
        assert result.scoring_results['final_score'] >= 70

    def test_redemption_theme_detection(self, mock_hf_analyzer, redemption_song):
        """Test redemption theme detection."""
        # Mock zero-shot classification for redemption themes
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Redemption and deliverance', 'score': 0.94},
            {'label': 'Grace and mercy', 'score': 0.87},
            {'label': 'Freedom from sin', 'score': 0.85}
        ]
        
        # Mock other analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.86}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.94}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'joy', 'score': 0.80}]
        
        result = mock_hf_analyzer.analyze_song(
            redemption_song["title"],
            redemption_song["artist"],
            redemption_song["lyrics"]
        )
        
        # Expected: +7 points for redemption theme
        assert result is not None
        
        # Check for redemption themes
        themes = result.biblical_analysis.get('themes', [])
        redemption_keywords = ['redeemed', 'redemption', 'grace', 'delivered', 'bought']
        redemption_themes_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in redemption_keywords)
            for t in themes
        )
        assert redemption_themes_found, "Should detect redemption themes"

    def test_sacrificial_love_detection(self, mock_hf_analyzer, sacrificial_love_song):
        """Test sacrificial love theme detection."""
        # Mock zero-shot classification for sacrificial love
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Sacrificial love', 'score': 0.92},
            {'label': 'Self-giving love', 'score': 0.89},
            {'label': 'Christlike love', 'score': 0.86}
        ]
        
        # Mock other analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.84}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.93}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'love', 'score': 0.88}]
        
        result = mock_hf_analyzer.analyze_song(
            sacrificial_love_song["title"],
            sacrificial_love_song["artist"],
            sacrificial_love_song["lyrics"]
        )
        
        # Expected: +6 points for sacrificial love theme
        assert result is not None
        
        # Check for love themes
        themes = result.biblical_analysis.get('themes', [])
        love_keywords = ['love', 'sacrifice', 'lay down', 'gave', 'self-giving']
        love_themes_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in love_keywords)
            for t in themes
        )
        assert love_themes_found, "Should detect sacrificial love themes"

    def test_light_vs_darkness_detection(self, mock_hf_analyzer, light_vs_darkness_song):
        """Test light vs darkness spiritual theme detection."""
        # Mock zero-shot classification for spiritual warfare
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Light overcoming darkness', 'score': 0.90},
            {'label': 'Spiritual victory', 'score': 0.87},
            {'label': 'Jesus as light', 'score': 0.85}
        ]
        
        # Mock other analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.83}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.92}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'joy', 'score': 0.79}]
        
        result = mock_hf_analyzer.analyze_song(
            light_vs_darkness_song["title"],
            light_vs_darkness_song["artist"],
            light_vs_darkness_song["lyrics"]
        )
        
        # Expected: +5 points for light vs darkness theme
        assert result is not None
        
        # Check for light/darkness themes
        themes = result.biblical_analysis.get('themes', [])
        light_keywords = ['light', 'darkness', 'overcome', 'victory', 'breaking chains']
        light_themes_found = any(
            any(keyword in t.get('theme', '').lower() for keyword in light_keywords)
            for t in themes
        )
        assert light_themes_found, "Should detect light vs darkness themes"

    def test_false_positive_prevention(self, mock_hf_analyzer, secular_song):
        """Test that secular songs don't trigger false positive gospel themes."""
        # Mock zero-shot classification showing low scores for gospel themes
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Party and celebration', 'score': 0.95},
            {'label': 'Materialism', 'score': 0.88},
            {'label': 'Worldly values', 'score': 0.82}
        ]
        
        # Mock other analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.75}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.85}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'joy', 'score': 0.70}]
        
        result = mock_hf_analyzer.analyze_song(
            secular_song["title"],
            secular_song["artist"],
            secular_song["lyrics"]
        )
        
        # Expected: No false positive gospel themes
        assert result is not None
        
        # Check that no significant gospel themes were detected
        themes = result.biblical_analysis.get('themes', [])
        gospel_keywords = ['christ', 'jesus', 'gospel', 'redemption', 'salvation']
        false_gospel_themes = any(
            any(keyword in t.get('theme', '').lower() for keyword in gospel_keywords)
            for t in themes
        )
        assert not false_gospel_themes, "Secular songs should not trigger gospel theme false positives"
        
        # Score should be low (not high like gospel songs)
        assert result.scoring_results['final_score'] < 50, "Secular songs should not score as highly as gospel songs"

    def test_theme_confidence_scoring(self, mock_hf_analyzer):
        """Test that theme detection includes confidence scores."""
        # Mock high-confidence theme detection
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Christ-centered worship', 'score': 0.95},
            {'label': 'Gospel presentation', 'score': 0.92}
        ]
        
        # Mock other analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.85}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.90}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'joy', 'score': 0.80}]
        
        result = mock_hf_analyzer.analyze_song(
            "Test Song",
            "Test Artist",
            "Jesus Christ is Lord and Savior"
        )
        
        # Check that confidence scores are included
        assert result is not None
        themes = result.biblical_analysis.get('themes', [])
        
        # Each theme should have a confidence score
        for theme in themes:
            assert 'score' in theme, "Each detected theme should include confidence score"
            assert 0 <= theme['score'] <= 1, "Confidence scores should be between 0 and 1"

    def test_zero_shot_classification_integration(self, mock_hf_analyzer):
        """Test that zero-shot classification is properly integrated."""
        # This test ensures the new BART model integration works
        mock_hf_analyzer._theme_analyzer.return_value = [
            {'label': 'Christ-centered worship', 'score': 0.93},
            {'label': 'Gospel message', 'score': 0.88}
        ]
        
        # Mock other required analyzers
        mock_hf_analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.85}]
        mock_hf_analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.90}]
        mock_hf_analyzer._emotion_analyzer.return_value = [{'label': 'joy', 'score': 0.80}]
        
        result = mock_hf_analyzer.analyze_song(
            "Amazing Grace",
            "Traditional",
            "Amazing grace how sweet the sound that saved a wretch like me"
        )
        
        # Verify that the theme analyzer was called (integration test)
        assert result is not None
        assert mock_hf_analyzer._theme_analyzer.called, "Zero-shot theme analyzer should be called"
        
        # Verify result structure includes enhanced theme analysis
        assert 'biblical_analysis' in result.__dict__ or hasattr(result, 'biblical_analysis')
        assert 'scoring_results' in result.__dict__ or hasattr(result, 'scoring_results')


class TestCoreGospelThemesScoring:
    """Test scoring logic for Core Gospel Themes."""
    
    def test_christ_centered_scoring(self):
        """Test that Christ-centered themes award +10 points."""
        # This will be implemented when we create the enhanced scoring system
        pass
    
    def test_gospel_presentation_scoring(self):
        """Test that gospel presentation themes award +10 points."""
        pass
    
    def test_redemption_scoring(self):
        """Test that redemption themes award +7 points."""
        pass
    
    def test_sacrificial_love_scoring(self):
        """Test that sacrificial love themes award +6 points."""
        pass
    
    def test_light_vs_darkness_scoring(self):
        """Test that light vs darkness themes award +5 points."""
        pass
    
    def test_cumulative_scoring(self):
        """Test that multiple themes accumulate points correctly."""
        pass
    
    def test_score_range_validation(self):
        """Test that final scores stay within 0-100 range."""
        pass 