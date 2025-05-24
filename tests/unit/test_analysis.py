import pytest
from unittest.mock import patch, MagicMock, Mock
from app.utils.analysis import SongAnalyzer
from app.utils.lyrics import LyricsFetcher 
from app.utils.bible_client import BibleClient
import torch

# Fixtures
@pytest.fixture
def mock_hf_transformers():
    with patch('transformers.pipeline') as mock_pipeline, \
         patch('transformers.AutoModelForSequenceClassification.from_pretrained') as mock_model, \
         patch('transformers.AutoTokenizer.from_pretrained') as mock_tokenizer:
        mock_pipeline.return_value = MagicMock()
        yield mock_pipeline, mock_model, mock_tokenizer

@pytest.fixture
def mock_vader():
    with patch('vaderSentiment.vaderSentiment.SentimentIntensityAnalyzer') as mock_vader_class:
        mock_vader = MagicMock()
        mock_vader.polarity_scores.return_value = {'compound': 0.5}
        mock_vader_class.return_value = mock_vader
        yield mock_vader

@pytest.fixture
def analyzer(mock_hf_transformers, mock_vader):
    lyrics_fetcher = MagicMock(spec=LyricsFetcher)
    bible_client = MagicMock(spec=BibleClient)
    return SongAnalyzer(lyrics_fetcher, bible_client)

class TestSongAnalyzer:
    def test_analyze_song_success_path(self, analyzer, mock_hf_transformers, mock_vader):
        # Mock the lyrics fetcher to return clean lyrics
        test_lyrics = "God is good, a song of faith and joy."
        # Create a mock for the fetch_lyrics method
        analyzer.lyrics_fetcher = MagicMock()
        analyzer.lyrics_fetcher.fetch_lyrics.return_value = test_lyrics
    
        # Mock the content moderation map in the rubric
        with patch.dict(analyzer.christian_rubric['purity_flag_definitions'], {
            'content_moderation_map': {
                'safe': {
                    'flag_name': 'Safe Content',
                    'penalty': 0
                }
            },
            'cardiffnlp_model_map': {
                'hate': {
                    'flag_name': 'Hate Speech Detected',
                    'penalty': 75
                },
                'offensive': {
                    'flag_name': 'Explicit Language / Corrupting Talk',
                    'penalty': 50
                }
            }
        }):
            # Patch the internal methods
            with patch.object(analyzer, '_get_content_moderation_predictions', 
                           return_value=[{'label': 'safe', 'score': 0.9}]) as mock_get_predictions, \
                 patch.object(analyzer, '_detect_christian_themes', 
                           return_value=([], [])), \
                 patch.object(analyzer, '_detect_christian_purity_flags',
                           return_value=([], 0)) as mock_detect_purity_flags:
                
                # Call the method under test
                result = analyzer.analyze_song("Good Song", "Good Artist")

            # Verify the results
            assert not result['errors'], f"Expected no errors, but got: {result['errors']}"
            # The lyrics should be preprocessed (lowercase, no punctuation)
            assert result['lyrics_used_for_analysis'] == 'god is good a song of faith and joy'
            # Score should be 100 (baseline) + 0 (no penalties) + 0 (no themes) = 100
            assert result['christian_score'] == 100, f"Expected score 100, got {result['christian_score']}"
            assert result['christian_concern_level'] == 'Low', \
                f"Expected 'Low' concern level, got {result['christian_concern_level']}"
            
            # Verify no purity flags were triggered
            purity_flags = result.get('christian_purity_flags_details', [])
            assert not any(flag['penalty_applied'] > 0 for flag in purity_flags), \
                f"Expected no purity flags with penalty > 0, but got: {purity_flags}"
            
            # Verify no themes were detected
            assert not result['christian_positive_themes_detected'], \
                f"Expected no positive themes, but got: {result['christian_positive_themes_detected']}"
            assert not result['christian_negative_themes_detected'], \
                f"Expected no negative themes, but got: {result['christian_negative_themes_detected']}"
            
            # Verify the mocks were called as expected
            expected_lyrics = 'god is good a song of faith and joy'
            mock_get_predictions.assert_called_once_with(expected_lyrics)
            mock_detect_purity_flags.assert_called_once()

    def test_analyze_song_with_offensive_content(self, analyzer, mock_hf_transformers, mock_vader):
        # Test with lyrics that should trigger offensive content detection
        test_lyrics = "This song has some offensive words and hate speech."
        analyzer.lyrics_fetcher = MagicMock()
        analyzer.lyrics_fetcher.fetch_lyrics.return_value = test_lyrics
        
        # Mock the content moderation predictions to return offensive content
        with patch.object(analyzer, '_get_content_moderation_predictions', 
                       return_value=[{'label': 'offensive', 'score': 0.95}]) as mock_get_predictions, \
             patch.object(analyzer, '_detect_christian_themes', 
                       return_value=([], [])), \
             patch.object(analyzer, '_detect_christian_purity_flags',
                       return_value=([{'flag': 'Explicit Language / Corrupting Talk', 'penalty_applied': 50, 'confidence': 0.95}], 50)) as mock_detect_purity_flags, \
             patch.object(analyzer, '_calculate_christian_score_and_concern',
                       return_value=(50, 'High')) as mock_calculate_score:
            
            # Call the method under test
            result = analyzer.analyze_song("Offensive Song", "Bad Artist")

        # Verify the results
        assert not result['errors'], f"Expected no errors, but got: {result['errors']}"
        # The score should be 50 (mocked return value)
        assert result['christian_score'] == 50, f"Expected score 50, got {result['christian_score']}"
        # Concern level should be High (mocked return value)
        assert result['christian_concern_level'] == 'High', \
            f"Expected 'High' concern level, got {result['christian_concern_level']}"
        
        # Verify purity flags were triggered
        purity_flags = result.get('christian_purity_flags_details', [])
        assert any(flag.get('penalty_applied', 0) > 0 for flag in purity_flags), \
            f"Expected purity flags with penalty > 0, but got: {purity_flags}"

    def test_analyze_song_with_positive_themes(self, analyzer, mock_hf_transformers, mock_vader):
        # Test with lyrics that contain positive Christian themes
        test_lyrics = "Praise the Lord for His wonderful works. We trust in His grace."
        analyzer.lyrics_fetcher = MagicMock()
        analyzer.lyrics_fetcher.fetch_lyrics.return_value = test_lyrics
        
        # Mock the content moderation predictions to return safe content
        with patch.object(analyzer, '_get_content_moderation_predictions', 
                       return_value=[{'label': 'safe', 'score': 0.9}]) as mock_get_predictions, \
             patch.object(analyzer, '_detect_christian_themes', 
                       return_value=([
                           {'theme': 'Worship / Glorifying God', 'score': 0.9, 'verses': ['Psalm 95:6']},
                            {'theme': 'Faith / Trust in God', 'score': 0.85, 'verses': ['Proverbs 3:5-6']}
                       ], [])), \
             patch.object(analyzer, '_detect_christian_purity_flags',
                       return_value=([], 0)) as mock_detect_purity_flags:
            
            # Call the method under test
            result = analyzer.analyze_song("Praise Song", "Good Artist")

        # Verify the results
        assert not result['errors'], f"Expected no errors, but got: {result['errors']}"
        # The score should be 100 (baseline) + (2 * 5 for themes) = 110, but capped at 100
        assert result['christian_score'] == 100, f"Expected score 100, got {result['christian_score']}"
        assert result['christian_concern_level'] == 'Low', \
            f"Expected 'Low' concern level, got {result['christian_concern_level']}"
        
        # Verify themes were detected
        assert len(result['christian_positive_themes_detected']) == 2, \
            f"Expected 2 positive themes, got {result['christian_positive_themes_detected']}"
        assert not result['christian_negative_themes_detected'], \
            f"Expected no negative themes, but got: {result['christian_negative_themes_detected']}"

    def test_analyze_song_with_lyrics_fetch_error(self, analyzer, mock_hf_transformers, mock_vader):
        # Test error handling when lyrics fetching fails
        error_msg = "Failed to fetch lyrics"
        analyzer.lyrics_fetcher = MagicMock()
        analyzer.lyrics_fetcher.fetch_lyrics.side_effect = Exception(error_msg)
        
        # Call the method under test
        result = analyzer.analyze_song("Nonexistent Song", "Unknown Artist")
        
        # Verify the error was handled
        assert 'errors' in result, "Expected errors in result"
        assert any(error_msg in error for error in result['errors']), \
            f"Expected error message containing '{error_msg}' in {result['errors']}"
        # Should use the baseline score when lyrics can't be fetched
        assert result['christian_score'] == 100, f"Expected score 100, got {result['christian_score']}"
        # With no lyrics, we can't determine concern level, so it should be Low (default)
        assert result['christian_concern_level'] == 'Low', \
            f"Expected 'Low' concern level, got {result['christian_concern_level']}"


class TestDetectChristianPurityFlags:
    """Test cases for _detect_christian_purity_flags method."""
    
    @pytest.fixture
    def analyzer(self):
        """Fixture to create a SongAnalyzer instance with mocked dependencies."""
        analyzer = SongAnalyzer()
        # Mock the rubric with our test configuration
        analyzer.christian_rubric = {
            "baseline_score": 100,
            "purity_flag_definitions": {
                "cardiffnlp_model_map": {
                    "hate": {"flag_name": "Hate Speech Detected", "penalty": 75},
                    "hate/threatening": {"flag_name": "Hate Speech / Threats", "penalty": 80},
                    "harassment": {"flag_name": "Harassment / Bullying", "penalty": 60},
                    "self-harm": {"flag_name": "Self-Harm / Suicide Content", "penalty": 70},
                    "sexual": {"flag_name": "Sexual Content / Impurity (overt)", "penalty": 50},
                    "violence": {"flag_name": "Violent Content", "penalty": 60},
                },
                "other_flags": {
                    "drugs": {
                        "keywords": ["drug", "cocaine", "heroin", "marijuana"],
                        "flag_name": "Glorification of Drugs / Substance Abuse",
                        "penalty": 25
                    },
                    "explicit_language": {
                        "keywords": ["fuck", "shit", "bitch", "asshole"],
                        "flag_name": "Explicit Language / Corrupting Talk",
                        "penalty": 30
                    }
                }
            }
        }
        return analyzer

    def test_no_flags_detected(self, analyzer):
        """Test when no flags should be detected."""
        # Mock predictions with only safe content
        predictions = [{"label": "safe", "score": 0.9}]
        lyrics = "This is a clean song with no issues."
        
        flags, penalty = analyzer._detect_christian_purity_flags(predictions, lyrics)
        
        assert len(flags) == 0
        assert penalty == 0

    def test_hate_speech_detection(self, analyzer):
        """Test detection of hate speech with high confidence."""
        predictions = [
            {"label": "hate", "score": 0.95},
            {"label": "safe", "score": 0.05}
        ]
        lyrics = "This song contains hate speech."
        
        flags, penalty = analyzer._detect_christian_purity_flags(predictions, lyrics)
        
        assert len(flags) == 1
        assert flags[0]["flag"] == "Hate Speech Detected"
        assert flags[0]["penalty_applied"] == 75
        assert penalty == 75

    def test_sexual_content_detection(self, analyzer):
        """Test detection of sexual content with medium confidence."""
        predictions = [
            {"label": "sexual", "score": 0.75},
            {"label": "safe", "score": 0.25}
        ]
        lyrics = "This song has some suggestive content."
        
        flags, penalty = analyzer._detect_christian_purity_flags(predictions, lyrics)
        
        assert len(flags) == 1
        assert flags[0]["flag"] == "Sexual Content / Impurity (overt)"
        assert flags[0]["penalty_applied"] == 50
        assert penalty == 50

    def test_keyword_based_drug_detection(self, analyzer):
        """Test detection of drug-related content via keywords."""
        predictions = [{"label": "safe", "score": 0.9}]
        lyrics = "Let's get high on marijuana and forget our problems."
        
        flags, penalty = analyzer._detect_christian_purity_flags(predictions, lyrics)
        
        assert len(flags) == 1
        assert flags[0]["flag"] == "Glorification of Drugs / Substance Abuse"
        assert flags[0]["penalty_applied"] == 25
        assert penalty == 25

    def test_keyword_based_explicit_language(self, analyzer):
        """Test detection of explicit language via keywords."""
        predictions = [{"label": "safe", "score": 0.9}]
        lyrics = "I don't give a fuck about your rules."
        
        flags, penalty = analyzer._detect_christian_purity_flags(predictions, lyrics)
        
        assert len(flags) == 1
        assert flags[0]["flag"] == "Explicit Language / Corrupting Talk"
        assert flags[0]["penalty_applied"] == 30
        assert penalty == 30

    def test_multiple_flags(self, analyzer):
        """Test detection of multiple flags with different sources."""
        predictions = [
            {"label": "hate", "score": 0.8},
            {"label": "violence", "score": 0.7}
        ]
        lyrics = "Let's get marijuana and start a riot!"
        
        flags, penalty = analyzer._detect_christian_purity_flags(predictions, lyrics)
        
        # Should have 3 flags: hate, violence, and drugs (from keyword)
        assert len(flags) == 3
        flag_names = {f["flag"] for f in flags}
        assert "Hate Speech Detected" in flag_names
        assert "Violent Content" in flag_names
        assert "Glorification of Drugs / Substance Abuse" in flag_names
        # Total would be 75 (hate) + 60 (violence) + 25 (drugs) = 160, but capped at 100
        assert penalty == 100  # Capped at 100

    def test_low_confidence_predictions(self, analyzer):
        """Test that low confidence predictions are ignored."""
        predictions = [
            {"label": "hate", "score": 0.3},  # Below threshold
            {"label": "safe", "score": 0.7}
        ]
        lyrics = "This might be hate speech, but the model isn't sure."
        
        flags, penalty = analyzer._detect_christian_purity_flags(predictions, lyrics)
        
        assert len(flags) == 0
        assert penalty == 0

    def test_penalty_capping(self, analyzer):
        """Test that the total penalty is capped at 100."""
        predictions = [
            {"label": "hate", "score": 0.95},
            {"label": "violence", "score": 0.9},
            {"label": "sexual", "score": 0.85}
        ]
        lyrics = "This song has multiple issues that would exceed the penalty cap."
        
        flags, penalty = analyzer._detect_christian_purity_flags(predictions, lyrics)
        
        assert penalty == 100
        assert sum(f["penalty_applied"] for f in flags) > 100  # Individual penalties exceed cap

    def test_empty_lyrics(self, analyzer):
        """Test behavior with empty lyrics."""
        predictions = [{"label": "safe", "score": 0.9}]
        flags, penalty = analyzer._detect_christian_purity_flags(predictions, "")
        
        assert len(flags) == 0
        assert penalty == 0

    def test_none_lyrics(self, analyzer):
        """Test behavior with None lyrics."""
        predictions = [{"label": "safe", "score": 0.9}]
        flags, penalty = analyzer._detect_christian_purity_flags(predictions, None)
        
        assert len(flags) == 0
        assert penalty == 0
