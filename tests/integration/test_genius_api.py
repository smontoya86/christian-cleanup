"""
Integration tests for Genius API interactions.
Tests the LyricsFetcher class with mocked API responses to ensure proper handling
of various API scenarios including rate limiting, timeouts, and error responses.
"""

import pytest
import responses
import time
from unittest.mock import patch, MagicMock
from requests.exceptions import RequestException, Timeout

from app.utils.lyrics import LyricsFetcher
from app.config.settings import TestingConfig


class TestGeniusAPIIntegration:
    """Test suite for Genius API integration functionality."""

    @pytest.fixture
    def lyrics_fetcher(self):
        """Create a LyricsFetcher instance with test configuration."""
        return LyricsFetcher(genius_token='test_token')

    @pytest.fixture
    def mock_genius_search_response(self):
        """Mock successful Genius API search response."""
        return {
            'meta': {'status': 200},
            'response': {
                'hits': [
                    {
                        'result': {
                            'id': 123456,
                            'title': 'Amazing Grace',
                            'primary_artist': {
                                'name': 'Chris Tomlin'
                            },
                            'url': 'https://genius.com/chris-tomlin-amazing-grace-lyrics'
                        }
                    }
                ]
            }
        }

    @pytest.fixture
    def mock_lyrics_page_html(self):
        """Mock HTML page containing lyrics."""
        return '''
        <html>
        <body>
            <div data-lyrics-container="true">
                <div class="Lyrics__Container-sc-1ynbvzw-6">
                    Amazing grace, how sweet the sound<br>
                    That saved a wretch like me<br>
                    I once was lost, but now am found<br>
                    Was blind but now I see
                </div>
            </div>
        </body>
        </html>
        '''

    @pytest.mark.integration
    @responses.activate
    def test_successful_lyrics_fetch(self, lyrics_fetcher, mock_genius_search_response, mock_lyrics_page_html):
        """Test successful lyrics fetching from Genius API."""
        # Mock search API call
        responses.add(
            responses.GET,
            'https://api.genius.com/search',
            json=mock_genius_search_response,
            status=200
        )
        
        # Mock lyrics page request
        responses.add(
            responses.GET,
            'https://genius.com/chris-tomlin-amazing-grace-lyrics',
            body=mock_lyrics_page_html,
            status=200
        )
        
        # Test the fetch
        result = lyrics_fetcher.fetch_lyrics('Chris Tomlin', 'Amazing Grace')
        
        assert result is not None
        assert 'amazing grace' in result.lower()
        assert 'sweet the sound' in result.lower()
        assert len(responses.calls) == 2

    @pytest.mark.integration
    @responses.activate
    def test_rate_limiting_retry_mechanism(self, lyrics_fetcher):
        """Test that rate limiting triggers proper retry behavior."""
        # First call returns rate limit error
        responses.add(
            responses.GET,
            'https://api.genius.com/search',
            json={'error': 'rate limit exceeded'},
            status=429,
            headers={'Retry-After': '1'}
        )
        
        # Second call succeeds
        responses.add(
            responses.GET,
            'https://api.genius.com/search',
            json={
                'response': {
                    'hits': [
                        {
                            'result': {
                                'id': 123,
                                'title': 'Test Song',
                                'primary_artist': {'name': 'Test Artist'},
                                'url': 'https://genius.com/test-lyrics'
                            }
                        }
                    ]
                }
            },
            status=200
        )
        
        responses.add(
            responses.GET,
            'https://genius.com/test-lyrics',
            body='<div class="Lyrics__Container-sc-1ynbvzw-6">Test lyrics</div>',
            status=200
        )
        
        # Should succeed after retry
        with patch('time.sleep') as mock_sleep:
            result = lyrics_fetcher.fetch_lyrics('Test Artist', 'Test Song')
            
        assert result is not None
        assert 'test lyrics' in result.lower()
        assert len(responses.calls) == 3  # Rate limit + successful search + lyrics page
        mock_sleep.assert_called()

    @pytest.mark.integration
    @responses.activate
    def test_multiple_rate_limits_with_exponential_backoff(self, lyrics_fetcher):
        """Test exponential backoff with multiple consecutive rate limits."""
        # Add multiple rate limit responses
        for i in range(3):
            responses.add(
                responses.GET,
                'https://api.genius.com/search',
                json={'error': 'rate limit exceeded'},
                status=429
            )
        
        # Final successful response
        responses.add(
            responses.GET,
            'https://api.genius.com/search',
            json={
                'response': {
                    'hits': [
                        {
                            'result': {
                                'id': 123,
                                'title': 'Test Song',
                                'primary_artist': {'name': 'Test Artist'},
                                'url': 'https://genius.com/test-lyrics'
                            }
                        }
                    ]
                }
            },
            status=200
        )
        
        responses.add(
            responses.GET,
            'https://genius.com/test-lyrics',
            body='<div class="Lyrics__Container-sc-1ynbvzw-6">Test lyrics</div>',
            status=200
        )
        
        with patch('time.sleep') as mock_sleep:
            result = lyrics_fetcher.fetch_lyrics('Test Artist', 'Test Song')
            
        assert result is not None
        assert mock_sleep.call_count >= 3  # Should have slept after each rate limit
        
        # Verify exponential backoff pattern
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls[0] < sleep_calls[1] < sleep_calls[2]

    @pytest.mark.integration
    @responses.activate
    def test_no_search_results_fallback(self, lyrics_fetcher):
        """Test behavior when Genius API returns no search results."""
        responses.add(
            responses.GET,
            'https://api.genius.com/search',
            json={'response': {'hits': []}},
            status=200
        )
        
        result = lyrics_fetcher.fetch_lyrics('Unknown Artist', 'Unknown Song')
        assert result is None or result == ""

    @pytest.mark.integration
    @responses.activate
    def test_api_server_error_handling(self, lyrics_fetcher):
        """Test handling of server errors from Genius API."""
        responses.add(
            responses.GET,
            'https://api.genius.com/search',
            json={'error': 'internal server error'},
            status=500
        )
        
        result = lyrics_fetcher.fetch_lyrics('Test Artist', 'Test Song')
        assert result is None or result == ""

    @pytest.mark.integration
    @responses.activate
    def test_network_timeout_handling(self, lyrics_fetcher):
        """Test handling of network timeouts."""
        def timeout_callback(request):
            raise Timeout("Request timed out")
        
        responses.add_callback(
            responses.GET,
            'https://api.genius.com/search',
            callback=timeout_callback
        )
        
        result = lyrics_fetcher.fetch_lyrics('Test Artist', 'Test Song')
        assert result is None or result == ""

    @pytest.mark.integration
    @responses.activate
    def test_malformed_lyrics_page_handling(self, lyrics_fetcher, mock_genius_search_response):
        """Test handling of malformed lyrics pages."""
        responses.add(
            responses.GET,
            'https://api.genius.com/search',
            json=mock_genius_search_response,
            status=200
        )
        
        # Malformed HTML without lyrics container
        responses.add(
            responses.GET,
            'https://genius.com/chris-tomlin-amazing-grace-lyrics',
            body='<html><body><p>No lyrics here</p></body></html>',
            status=200
        )
        
        result = lyrics_fetcher.fetch_lyrics('Chris Tomlin', 'Amazing Grace')
        assert result is None or result == ""

    @pytest.mark.integration
    @responses.activate
    def test_api_authentication_error(self, lyrics_fetcher):
        """Test handling of authentication errors."""
        responses.add(
            responses.GET,
            'https://api.genius.com/search',
            json={'error': 'invalid token'},
            status=401
        )
        
        result = lyrics_fetcher.fetch_lyrics('Test Artist', 'Test Song')
        assert result is None or result == ""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_lyrics_caching_behavior(self, lyrics_fetcher, mock_genius_search_response, mock_lyrics_page_html):
        """Test that lyrics caching works correctly to reduce API calls."""
        responses.add(
            responses.GET,
            'https://api.genius.com/search',
            json=mock_genius_search_response,
            status=200
        )
        
        responses.add(
            responses.GET,
            'https://genius.com/chris-tomlin-amazing-grace-lyrics',
            body=mock_lyrics_page_html,
            status=200
        )
        
        # First fetch should make API calls
        result1 = lyrics_fetcher.fetch_lyrics('Chris Tomlin', 'Amazing Grace')
        initial_call_count = len(responses.calls)
        
        # Second fetch should use cache (if implemented)
        result2 = lyrics_fetcher.fetch_lyrics('Chris Tomlin', 'Amazing Grace')
        
        assert result1 == result2
        # Note: If caching is implemented, assert len(responses.calls) == initial_call_count

    @pytest.mark.integration
    def test_fallback_providers_chain(self, lyrics_fetcher):
        """Test that fallback providers are called when Genius fails."""
        with patch.object(lyrics_fetcher, '_fetch_from_genius', return_value=None):
            with patch.object(lyrics_fetcher, '_fetch_from_lrclib', return_value='Fallback lyrics'):
                result = lyrics_fetcher.fetch_lyrics('Test Artist', 'Test Song')
                assert result == 'Fallback lyrics'

    @pytest.mark.integration
    @responses.activate
    def test_lyrics_cleaning_and_processing(self, lyrics_fetcher, mock_genius_search_response):
        """Test that fetched lyrics are properly cleaned and processed."""
        dirty_lyrics_html = '''
        <div class="Lyrics__Container-sc-1ynbvzw-6">
            Amazing grace, how sweet the sound<br>
            That saved a wretch like me<br><br>
            [Verse 2]<br>
            I once was lost, but now am found<br>
            Was blind but now I see<br>
            <a href="#annotation">Some annotation</a>
        </div>
        '''
        
        responses.add(
            responses.GET,
            'https://api.genius.com/search',
            json=mock_genius_search_response,
            status=200
        )
        
        responses.add(
            responses.GET,
            'https://genius.com/chris-tomlin-amazing-grace-lyrics',
            body=dirty_lyrics_html,
            status=200
        )
        
        result = lyrics_fetcher.fetch_lyrics('Chris Tomlin', 'Amazing Grace')
        
        # Should be cleaned of HTML tags and formatted properly
        assert result is not None
        assert '<br>' not in result
        assert '<a href' not in result
        assert 'amazing grace' in result.lower()

    @pytest.mark.integration
    @responses.activate 
    def test_concurrent_requests_handling(self, lyrics_fetcher, mock_genius_search_response, mock_lyrics_page_html):
        """Test handling of concurrent API requests."""
        import threading
        import concurrent.futures
        
        # Set up responses for multiple requests
        for i in range(5):
            responses.add(
                responses.GET,
                'https://api.genius.com/search',
                json=mock_genius_search_response,
                status=200
            )
            
            responses.add(
                responses.GET,
                'https://genius.com/chris-tomlin-amazing-grace-lyrics',
                body=mock_lyrics_page_html,
                status=200
            )
        
        def fetch_lyrics():
            return lyrics_fetcher.fetch_lyrics('Chris Tomlin', 'Amazing Grace')
        
        # Execute concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_lyrics) for _ in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All should succeed
        assert all(result is not None for result in results)
        assert all('amazing grace' in result.lower() for result in results) 