import pytest
from unittest.mock import patch, MagicMock, Mock
from app.utils.analysis import SongAnalyzer
# Assuming LyricsFetcher is in app.utils.lyrics
from app.utils.lyrics import LyricsFetcher 
import torch

# Mock Flask's current_app.logger
@pytest.fixture
def mock_current_app_logger(autouse=True): # autouse to apply to all tests using SongAnalyzer
    with patch('app.utils.analysis.current_app') as mock_app, \
         patch('nltk.download') as mock_nltk_download, \
         patch('nltk.data.find', return_value=True) as mock_nltk_find: # Assume vader_lexicon is found
        mock_app.logger = MagicMock()
        yield mock_app.logger, mock_nltk_download, mock_nltk_find

@pytest.fixture
def mock_hf_transformers():
    with patch('app.utils.analysis.AutoTokenizer.from_pretrained') as mock_tokenizer_from_pretrained, \
         patch('app.utils.analysis.AutoModelForSequenceClassification.from_pretrained') as mock_model_from_pretrained:

        mock_tokenizer_instance = MagicMock()
        mock_tokenizer_from_pretrained.return_value = mock_tokenizer_instance
        mock_tokenizer_instance.to.return_value = mock_tokenizer_instance 

        mock_model_instance = Mock() 
        config_mock = Mock()
        config_mock.configure_mock(
            id2label = {0: 'INAPPROPRIATE', 1: 'APPROPRIATE'},
            label2id = {'INAPPROPRIATE': 0, 'APPROPRIATE': 1}
        )
        mock_model_instance.config = config_mock
        
        mock_output_object = MagicMock() 
        mock_output_object.logits = torch.tensor([[0.1, 0.9]]) # Default to appropriate for setup
        mock_model_instance.return_value = mock_output_object 
        mock_model_instance.to.return_value = mock_model_instance 
        mock_model_from_pretrained.return_value = mock_model_instance

        yield mock_tokenizer_from_pretrained, mock_model_from_pretrained, mock_tokenizer_instance, mock_model_instance

@pytest.fixture
def mock_vader():
    with patch('app.utils.analysis.SentimentIntensityAnalyzer') as mock_sia:
        mock_sia_instance = MagicMock()
        mock_sia_instance.polarity_scores.return_value = {'neg': 0.1, 'neu': 0.8, 'pos': 0.1, 'compound': 0.0} # Default neutral
        mock_sia.return_value = mock_sia_instance
        yield mock_sia_instance

@pytest.fixture
def analyzer(app, mock_current_app_logger, mock_hf_transformers, mock_vader): 
    # SongAnalyzer initialization will use the mocked components due to the patches
    with app.app_context(): 
        analyzer_instance = SongAnalyzer()
    analyzer_instance.lyrics_fetcher = MagicMock()
    return analyzer_instance

class TestSongAnalyzer:
    def test_preprocess_lyrics_empty(self, analyzer):
        assert analyzer._preprocess_lyrics("") == ""

    def test_preprocess_lyrics_simple(self, analyzer):
        assert analyzer._preprocess_lyrics("Hello World!") == "hello world"

    def test_preprocess_lyrics_with_timestamps_and_punctuation(self, analyzer):
        text = "[00:01.123] Test lyrics, with some punctuation (like this). And new\nlines."
        expected = "test lyrics with some punctuation like this and new lines"
        assert analyzer._preprocess_lyrics(text) == expected

    def test_preprocess_lyrics_mixed_case(self, analyzer):
        assert analyzer._preprocess_lyrics("MiXeD CaSe") == "mixed case"

    # --- Tests for _detect_sensitive_content --- 
    def test_detect_sensitive_content_appropriate(self, analyzer, mock_hf_transformers):
        _, _, _, mock_model_instance = mock_hf_transformers
        
        # The model instance itself is callable and returns an object with 'logits'
        mock_output_object = MagicMock()
        mock_output_object.logits = torch.tensor([[0.1, 0.9]]) # Logits for APPROPRIATE
        mock_model_instance.return_value = mock_output_object
        
        with patch('torch.softmax', return_value=torch.tensor([[0.2, 0.8]])) as mock_softmax, \
             patch('torch.argmax') as mock_torch_argmax: 
            mock_torch_argmax.return_value.item.return_value = 1
            result = analyzer._detect_sensitive_content("This is a clean sentence.")
            assert result['label'] == 'APPROPRIATE'
            assert result['score'] == pytest.approx(0.2) # Score for 'inappropriate' class (index 0)

    def test_detect_sensitive_content_inappropriate(self, analyzer, mock_hf_transformers):
        _, _, _, mock_model_instance = mock_hf_transformers
        
        mock_output_object = MagicMock()
        mock_output_object.logits = torch.tensor([[0.9, 0.1]]) # Logits for INAPPROPRIATE
        mock_model_instance.return_value = mock_output_object

        with patch('torch.softmax', return_value=torch.tensor([[0.8, 0.2]])) as mock_softmax, \
             patch('torch.argmax') as mock_torch_argmax: 
            mock_torch_argmax.return_value.item.return_value = 0
            result = analyzer._detect_sensitive_content("This is a bad sentence.")
            assert result['label'] == 'INAPPROPRIATE'
            assert result['score'] == pytest.approx(0.8)

    def test_detect_sensitive_content_empty_text(self, analyzer):
        result = analyzer._detect_sensitive_content("")
        assert result['label'] == 'SAFE'
        assert result['score'] == 1.0

    # --- Tests for _extract_themes_basic --- 
    def test_extract_themes_basic_faith(self, analyzer):
        lyrics = "I have faith in God and Jesus my Lord."
        themes = analyzer._extract_themes_basic(analyzer._preprocess_lyrics(lyrics))
        assert 'faith' in themes
        assert themes['faith']['present'] is True
        # Example: sum(1 for kw in ['faith', 'god', 'jesus', 'lord'] if kw in preprocessed_lyrics.split())
        assert themes['faith']['keyword_matches'] >= 4 

    def test_extract_themes_basic_no_themes(self, analyzer):
        lyrics = "The sky is blue and the grass is green."
        themes = analyzer._extract_themes_basic(analyzer._preprocess_lyrics(lyrics))
        assert not themes

    def test_extract_themes_empty_lyrics(self, analyzer):
        themes = analyzer._extract_themes_basic("")
        assert not themes

    # --- Tests for _analyze_sentiment_basic --- 
    def test_analyze_sentiment_positive(self, analyzer, mock_vader):
        mock_vader.polarity_scores.return_value = {'neg': 0.0, 'neu': 0.1, 'pos': 0.9, 'compound': 0.95}
        result = analyzer._analyze_sentiment_basic("This is a wonderful and happy song.")
        assert result['sentiment_label'] == 'POSITIVE'
        assert result['sentiment_score'] == 0.95

    def test_analyze_sentiment_negative(self, analyzer, mock_vader):
        mock_vader.polarity_scores.return_value = {'neg': 0.9, 'neu': 0.1, 'pos': 0.0, 'compound': -0.95}
        result = analyzer._analyze_sentiment_basic("This is a sad and terrible song.")
        assert result['sentiment_label'] == 'NEGATIVE'
        assert result['sentiment_score'] == -0.95

    def test_analyze_sentiment_neutral(self, analyzer, mock_vader):
        mock_vader.polarity_scores.return_value = {'neg': 0.1, 'neu': 0.8, 'pos': 0.1, 'compound': 0.0}
        result = analyzer._analyze_sentiment_basic("This song is about a table.")
        assert result['sentiment_label'] == 'NEUTRAL'
        assert result['sentiment_score'] == 0.0

    def test_analyze_sentiment_empty_lyrics(self, analyzer):
        result = analyzer._analyze_sentiment_basic("")
        assert result['sentiment_label'] == 'NEUTRAL'
        assert result['sentiment_score'] == 0.0

    # --- Tests for analyze_song (main method) ---
    def test_analyze_song_lyrics_not_found(self, analyzer):
        analyzer.lyrics_fetcher.fetch_lyrics.return_value = None
        result = analyzer.analyze_song("Unknown Song", "Unknown Artist")
        assert result['lyrics'] is None
        assert result['error'] == 'Lyrics not found'
        assert 'Could not analyze: Lyrics not found.' in result['analysis_summary']

    def test_analyze_song_success_path(self, analyzer, mock_hf_transformers, mock_vader):
        analyzer.lyrics_fetcher.fetch_lyrics.return_value = "God is good, a song of faith and joy."
        
        _, _, _, mock_hf_model_instance = mock_hf_transformers
        
        mock_output_obj_sensitive = MagicMock()
        mock_output_obj_sensitive.logits = torch.tensor([[0.1, 0.9]]) # Appropriate
        mock_hf_model_instance.return_value = mock_output_obj_sensitive
        
        with patch('torch.softmax', return_value=torch.tensor([[0.1, 0.9]])) as sf, \
             patch('torch.argmax') as am: 
            am.return_value.item.return_value = 1
            mock_vader.polarity_scores.return_value = {'neg': 0.0, 'neu': 0.1, 'pos': 0.9, 'compound': 0.85}
            result = analyzer.analyze_song("Good Song", "Good Artist")

            assert result['error'] is None
            assert result['lyrics'] == "God is good, a song of faith and joy."
            assert result['sensitive_content_analysis']['label'] == 'APPROPRIATE'
            assert result['detailed_theme_analysis'].get('faith', {}).get('present') is True
            assert result['detailed_theme_analysis'].get('peace_joy', {}).get('present') is True
            assert result['sentiment_analysis']['sentiment_label'] == 'POSITIVE'
            assert result['alignment_score'] > 10 # Expect a decent positive score
            assert "Content appears appropriate." in result['analysis_summary']
            assert "Identified positive themes: faith, peace_joy" in result['analysis_summary'] or \
                   "Identified positive themes: peace_joy, faith" in result['analysis_summary']

    def test_analyze_song_inappropriate_content(self, analyzer, mock_hf_transformers, mock_vader):
        analyzer.lyrics_fetcher.fetch_lyrics.return_value = "some really bad words here"
        
        _, _, _, mock_hf_model_instance = mock_hf_transformers
        
        mock_output_obj_sensitive = MagicMock()
        mock_output_obj_sensitive.logits = torch.tensor([[0.95, 0.05]]) # Inappropriate
        mock_hf_model_instance.return_value = mock_output_obj_sensitive

        with patch('torch.softmax', return_value=torch.tensor([[0.95, 0.05]])) as sf, \
             patch('torch.argmax') as am: 
            am.return_value.item.return_value = 0
            mock_vader.polarity_scores.return_value = {'neg': 0.8, 'neu': 0.2, 'pos': 0.0, 'compound': -0.9}
            result = analyzer.analyze_song("Bad Song", "Bad Artist")

            assert result['sensitive_content_analysis']['label'] == 'INAPPROPRIATE'
            assert result['sensitive_content_analysis']['score'] == pytest.approx(0.95)
            assert result['alignment_score'] == 0 # Changed from < 0 to == 0
            assert "High probability of inappropriate content" in result['analysis_summary']
