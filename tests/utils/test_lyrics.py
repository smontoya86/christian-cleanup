import pytest
import os
from unittest.mock import patch, MagicMock
from flask import current_app
import requests

from app.utils.lyrics import LyricsFetcher

@pytest.fixture
def mock_app_config(mocker, app):
    """Mocks flask.current_app.config for tests.
    The 'app' fixture (from conftest.py, managed by pytest-flask) ensures an app context
    is active, so current_app is available.
    """
    mock_config_data = {'LYRICSGENIUS_API_KEY': 'dummy_lyricsgenius_token'}
    
    m_config = MagicMock(spec=dict)
    m_config.get.side_effect = lambda key, default=None: mock_config_data.get(key, default)
    
    # Patch the 'config' attribute of current_app
    # The 'app' fixture ensures current_app is valid and context is active.
    mocker.patch.object(current_app, 'config', m_config)
    return m_config

@pytest.fixture
def mock_logger(mocker):
    return mocker.patch('app.utils.lyrics.logger')

class MockGeniusSong:
    def __init__(self, lyrics):
        self.lyrics = lyrics

# Test Initialization
def test_lyrics_fetcher_init_token_from_config(mock_app_config, mock_logger):
    with patch('app.utils.lyrics.lyricsgenius.Genius') as mock_genius_constructor:
        # Ensure os.environ does not have the key to isolate config test
        with patch.dict(os.environ, {}, clear=True):
            fetcher = LyricsFetcher()
        current_app.config.get.assert_called_with('LYRICSGENIUS_API_KEY')
        mock_genius_constructor.assert_called_once_with('dummy_lyricsgenius_token',
                                                        verbose=False,
                                                        remove_section_headers=True,
                                                        skip_non_songs=True,
                                                        timeout=15)
        assert fetcher.genius is not None
        mock_logger.info.assert_any_call("LyricsFetcher: Using LYRICSGENIUS_API_KEY from Flask app config.")
        mock_logger.info.assert_any_call("LyricsFetcher: LyricsGenius client initialized successfully.")

def test_lyrics_fetcher_init_no_token_in_config(mock_app_config, mock_logger):
    current_app.config.get.side_effect = lambda key, default=None: None if key == 'LYRICSGENIUS_API_KEY' else default
    
    with patch('app.utils.lyrics.lyricsgenius.Genius') as mock_genius_constructor:
        # Ensure os.environ is also empty for the key
        with patch.dict(os.environ, {}, clear=True):
            fetcher = LyricsFetcher()
        current_app.config.get.assert_called_with('LYRICSGENIUS_API_KEY') # It will try config first
        # It will then try os.environ, which is empty in this test context
        mock_genius_constructor.assert_not_called()
        assert fetcher.genius is None
        # Check for the specific warning when no token is found anywhere
        mock_logger.warning.assert_any_call(
            "LyricsFetcher: LYRICSGENIUS_API_KEY not found in Flask config or environment. "
            "Lyrics fetching via Genius API will likely fail."
        )

# New test for token from environment
def test_lyrics_fetcher_init_token_from_env(mock_app_config, mock_logger):
    # Simulate token not found in app.config
    current_app.config.get.side_effect = lambda key, default=None: None if key == 'LYRICSGENIUS_API_KEY' else default
    env_token = "test_env_token"

    with patch.dict(os.environ, {'LYRICSGENIUS_API_KEY': env_token}, clear=True):
        with patch('app.utils.lyrics.lyricsgenius.Genius') as mock_genius_constructor:
            fetcher = LyricsFetcher()
            current_app.config.get.assert_called_with('LYRICSGENIUS_API_KEY') # Will try config first
            mock_genius_constructor.assert_called_once_with(env_token,
                                                            verbose=False,
                                                            remove_section_headers=True,
                                                            skip_non_songs=True,
                                                            timeout=15)
            assert fetcher.genius is not None
            mock_logger.info.assert_any_call("LyricsFetcher: Using LYRICSGENIUS_API_KEY from environment variable.")
            mock_logger.info.assert_any_call("LyricsFetcher: LyricsGenius client initialized successfully.")

def test_lyrics_fetcher_init_explicit_token(mock_logger, app):
    explicit_token = "explicit_dummy_token"
    with patch('app.utils.lyrics.lyricsgenius.Genius') as mock_genius_constructor:
        # Ensure config and environ are not the source for this test
        # When patching current_app.config itself, the 'get' method on the replacement MagicMock is what we check.
        replacement_config_mock = MagicMock(spec=dict)
        replacement_config_mock.get = MagicMock(return_value=None) # This is the mock for the 'get' method

        with patch.object(current_app, 'config', replacement_config_mock):
            with patch.dict(os.environ, {}, clear=True):
                fetcher = LyricsFetcher(genius_token=explicit_token)
        
        replacement_config_mock.get.assert_not_called() # Assert on the mocked 'get' method
        mock_genius_constructor.assert_called_once_with(explicit_token,
                                                        verbose=False, 
                                                        remove_section_headers=True, 
                                                        skip_non_songs=True, 
                                                        timeout=15)
        assert fetcher.genius is not None
        # We don't expect config/env specific logs if token is passed directly
        # but we expect the successful init log
        mock_logger.info.assert_any_call("LyricsFetcher: LyricsGenius client initialized successfully.")

def test_lyrics_fetcher_init_genius_exception(mock_app_config, mock_logger):
    # Simulate token being found in config to trigger Genius constructor attempt
    current_app.config.get.return_value = 'dummy_lyricsgenius_token' 
    
    with patch('app.utils.lyrics.lyricsgenius.Genius', side_effect=Exception("Genius Init Failed")) as mock_genius_constructor:
        with patch.dict(os.environ, {}, clear=True): # Ensure env is not a factor
            fetcher = LyricsFetcher()
        current_app.config.get.assert_called_with('LYRICSGENIUS_API_KEY')
        mock_genius_constructor.assert_called_once_with('dummy_lyricsgenius_token',
                                                        verbose=False, 
                                                        remove_section_headers=True, 
                                                        skip_non_songs=True, 
                                                        timeout=15)
        assert fetcher.genius is None
        mock_logger.error.assert_called_once_with("LyricsFetcher: Error initializing LyricsGenius client: Genius Init Failed")

# Test fetch_lyrics
@pytest.fixture
def lyrics_fetcher_instance(mock_app_config):
    with patch('lyricsgenius.Genius') as mock_genius_init:
        mock_genius_instance = MagicMock()
        mock_genius_init.return_value = mock_genius_instance
        fetcher = LyricsFetcher() # Uses mocked current_app.config via mock_app_config
        fetcher.genius = mock_genius_instance
        return fetcher

def test_fetch_lyrics_success(lyrics_fetcher_instance, mock_logger):
    mock_song = MockGeniusSong("Line 1\nLine 2\n\nLine 3")
    lyrics_fetcher_instance.genius.search_song.return_value = mock_song
    
    lyrics = lyrics_fetcher_instance.fetch_lyrics("Test Song", "Test Artist")
    
    lyrics_fetcher_instance.genius.search_song.assert_called_once_with("Test Song", "Test Artist")
    assert lyrics == "Line 1\nLine 2\nLine 3" # Expecting basic newline cleaning
    mock_logger.info.assert_any_call("Successfully fetched lyrics for 'Test Song' by 'Test Artist' from Genius.")

def test_fetch_lyrics_song_not_found(lyrics_fetcher_instance, mock_logger):
    lyrics_fetcher_instance.genius.search_song.return_value = None
    
    lyrics = lyrics_fetcher_instance.fetch_lyrics("Unknown Song", "Unknown Artist")
    
    lyrics_fetcher_instance.genius.search_song.assert_called_once_with("Unknown Song", "Unknown Artist")
    assert lyrics is None
    mock_logger.info.assert_any_call("Song 'Unknown Song' by 'Unknown Artist' not found on Genius or lyrics are empty.")

def test_fetch_lyrics_empty_lyrics(lyrics_fetcher_instance, mock_logger):
    mock_song = MockGeniusSong("") # Empty lyrics string
    lyrics_fetcher_instance.genius.search_song.return_value = mock_song

    lyrics = lyrics_fetcher_instance.fetch_lyrics("Empty Lyrics Song", "Test Artist")
    assert lyrics is None # Or an empty string, depends on desired behavior. Current code returns None if song.lyrics is falsy after strip.
    mock_logger.info.assert_any_call("Song 'Empty Lyrics Song' by 'Test Artist' not found on Genius or lyrics are empty.")

def test_fetch_lyrics_api_timeout_error(lyrics_fetcher_instance, mock_logger):
    lyrics_fetcher_instance.genius.search_song.side_effect = requests.exceptions.Timeout("API Timed Out")
    
    lyrics = lyrics_fetcher_instance.fetch_lyrics("Timeout Song", "Test Artist")
    
    assert lyrics is None
    mock_logger.error.assert_called_once_with("Timeout while fetching lyrics for 'Timeout Song' by 'Test Artist' from Genius.")

def test_fetch_lyrics_api_generic_error(lyrics_fetcher_instance, mock_logger):
    lyrics_fetcher_instance.genius.search_song.side_effect = Exception("Generic API Error")
    
    lyrics = lyrics_fetcher_instance.fetch_lyrics("Error Song", "Test Artist")
    
    assert lyrics is None
    mock_logger.error.assert_called_once_with("Error fetching lyrics for 'Error Song' by 'Test Artist' from Genius: Generic API Error")

def test_fetch_lyrics_no_genius_client(mock_app_config, mock_logger):
    current_app.config.get.side_effect = lambda key, default=None: None if key == 'LYRICSGENIUS_API_KEY' else default
    # Also ensure os.environ does not provide the key for this test
    with patch.dict(os.environ, {}, clear=True):
        fetcher = LyricsFetcher() # This will set fetcher.genius to None
    assert fetcher.genius is None

    lyrics = fetcher.fetch_lyrics("Some Song", "Some Artist")
    assert lyrics is None
    mock_logger.warning.assert_any_call("LyricsGenius client not initialized. Cannot fetch lyrics.")

def test_fetch_lyrics_missing_params(lyrics_fetcher_instance, mock_logger):
    # Test with no song title
    lyrics_no_title = lyrics_fetcher_instance.fetch_lyrics(None, "Test Artist")
    assert lyrics_no_title is None
    mock_logger.warning.assert_any_call("Song title and artist name are required to fetch lyrics.")
    
    # Test with no artist name
    mock_logger.reset_mock() # Reset mock for the next call
    lyrics_no_artist = lyrics_fetcher_instance.fetch_lyrics("Test Song", None)
    assert lyrics_no_artist is None
    mock_logger.warning.assert_any_call("Song title and artist name are required to fetch lyrics.")

# Test clean_lyrics (Basic tests, more in Subtask 6.3)
@pytest.fixture
def fetcher_for_cleaning(mock_app_config):
    # LyricsFetcher() init uses current_app.config, so app context is needed.
    # mock_app_config ensures it gets a dummy token.
    return LyricsFetcher()

def test_clean_lyrics_empty_input(fetcher_for_cleaning):
    assert fetcher_for_cleaning.clean_lyrics(None) == ""
    assert fetcher_for_cleaning.clean_lyrics("") == ""
    assert fetcher_for_cleaning.clean_lyrics("     ") == ""

def test_clean_lyrics_removes_section_headers(fetcher_for_cleaning):
    lyrics = "[Verse 1]\nHello world\n[Chorus]\nSinging loud"
    expected = "Hello world\nSinging loud"
    assert fetcher_for_cleaning.clean_lyrics(lyrics) == expected

def test_clean_lyrics_removes_bracket_annotations(fetcher_for_cleaning):
    lyrics = "Hello world [some annotation]\nSinging loud [another one]"
    expected = "Hello world\nSinging loud"
    assert fetcher_for_cleaning.clean_lyrics(lyrics) == expected

def test_clean_lyrics_removes_parentheses_metadata(fetcher_for_cleaning):
    lyrics = "Hello world (C) 2023\nSinging loud (Producer: Me)"
    # Current logic removes (C) 2023 and (Producer: Me) because they match specific patterns
    expected = "Hello world\nSinging loud"
    assert fetcher_for_cleaning.clean_lyrics(lyrics) == expected

def test_clean_lyrics_normalizes_newlines_and_strips(fetcher_for_cleaning):
    lyrics = "  Line 1  \n\n\n  Line 2  \n   \n  Line 3  "
    expected = "Line 1\nLine 2\nLine 3"
    assert fetcher_for_cleaning.clean_lyrics(lyrics) == expected

def test_clean_lyrics_integration_example(fetcher_for_cleaning, app):
    lyrics = "[Intro]\nOh yeah (This is it)\n\n[Verse 1]\nLine one here [annotation]\nLine two follows (Written by: You)\n\n[Chorus]\nSing it loud\nSing it proud\n\n(Outro - fade out...)\nGoodbye (x2)"
    # Expected output after cleaning logic (which removes (x2) and (Written by: You)):
    expected = "Oh yeah (This is it)\nLine one here\nLine two follows\nSing it loud\nSing it proud\n(Outro - fade out...)\nGoodbye"
    assert fetcher_for_cleaning.clean_lyrics(lyrics) == expected
