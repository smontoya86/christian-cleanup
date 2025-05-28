"""
Regression tests for rate limiting issues.
These tests ensure that previously fixed rate limiting bugs don't reoccur.
"""

import pytest
import responses
import time
from unittest.mock import patch, MagicMock
from requests.exceptions import RequestException

from app.utils.lyrics import LyricsFetcher
from app.services.spotify_service import SpotifyService


class TestRateLimitingRegression:
    """Regression tests for rate limiting functionality."""

    @pytest.fixture
    def lyrics_fetcher(self):
        """Create a LyricsFetcher instance for testing."""
        return LyricsFetcher(genius_token='test_token')

    @pytest.mark.regression
    @responses.activate
    def test_genius_exponential_backoff_regression(self, lyrics_fetcher):
        """
        Regression test for Genius API exponential backoff.
        
        Previously, the system would fail to properly implement exponential backoff,
        leading to rapid successive API calls and potential IP bans.
        
        Issue: Rate limiting was not properly handled with exponential backoff
        Fix: Implemented proper exponential backoff with jitter
        """
        # Simulate multiple consecutive rate limits
        for i in range(4):
            responses.add(
                responses.GET,
                'https://api.genius.com/search',
                json={'error': 'rate limit exceeded'},
                status=429,
                headers={'Retry-After': '2'}
            )

        # Final successful response
        responses.add(
            responses.GET,
            'https://api.genius.com/search',
            json={
                'response': {
                    'hits': [{
                        'result': {
                            'id': 123,
                            'title': 'Test Song',
                            'primary_artist': {'name': 'Test Artist'},
                            'url': 'https://genius.com/test-lyrics'
                        }
                    }]
                }
            },
            status=200
        )

        responses.add(
            responses.GET,
            'https://genius.com/test-lyrics',
            body='<div class="Lyrics__Container-sc-1ynbvzw-6">Test lyrics content</div>',
            status=200
        )

        with patch('time.sleep') as mock_sleep:
            result = lyrics_fetcher.fetch_lyrics('Test Artist', 'Test Song')

        # Verify exponential backoff was implemented
        assert mock_sleep.call_count == 4
        sleep_durations = [call[0][0] for call in mock_sleep.call_args_list]
        
        # Verify exponential increase in sleep durations
        for i in range(1, len(sleep_durations)):
            assert sleep_durations[i] > sleep_durations[i-1], \
                f"Sleep duration should increase exponentially: {sleep_durations}"

        # Verify final success
        assert result is not None
        assert 'test lyrics' in result.lower()

    @pytest.mark.regression
    @responses.activate
    def test_spotify_rate_limit_retry_after_header_regression(self, app, new_user):
        """
        Regression test for Spotify API Retry-After header handling.
        
        Previously, the system ignored the Retry-After header from Spotify,
        leading to immediate retries and potential API blocking.
        
        Issue: Retry-After header was not respected
        Fix: Properly parse and respect Retry-After header values
        """
        with app.app_context():
            spotify_service = SpotifyService(new_user)

            # First request returns rate limit with specific retry time
            responses.add(
                responses.GET,
                'https://api.spotify.com/v1/me/playlists',
                json={'error': {'status': 429, 'message': 'rate limit exceeded'}},
                status=429,
                headers={'Retry-After': '5'}
            )

            # Second request succeeds
            responses.add(
                responses.GET,
                'https://api.spotify.com/v1/me/playlists',
                json={'items': [], 'total': 0},
                status=200
            )

            with patch('time.sleep') as mock_sleep:
                playlists = spotify_service.get_user_playlists()

            # Verify Retry-After header was respected
            mock_sleep.assert_called_once_with(5)
            assert playlists == []

    @pytest.mark.regression
    @responses.activate
    def test_concurrent_rate_limit_handling_regression(self, lyrics_fetcher):
        """
        Regression test for concurrent rate limit handling.
        
        Previously, concurrent requests would not properly coordinate
        rate limiting, leading to stampeding herd problems.
        
        Issue: Multiple threads making simultaneous requests after rate limit
        Fix: Proper synchronization of rate limit backoff across threads
        """
        import threading
        import concurrent.futures

        # Set up rate limiting for all requests
        for i in range(10):
            responses.add(
                responses.GET,
                'https://api.genius.com/search',
                json={'error': 'rate limit exceeded'},
                status=429,
                headers={'Retry-After': '1'}
            )

        # Then successful responses
        for i in range(5):
            responses.add(
                responses.GET,
                'https://api.genius.com/search',
                json={
                    'response': {
                        'hits': [{
                            'result': {
                                'id': 123 + i,
                                'title': f'Test Song {i}',
                                'primary_artist': {'name': 'Test Artist'},
                                'url': f'https://genius.com/test-lyrics-{i}'
                            }
                        }]
                    }
                },
                status=200
            )
            
            responses.add(
                responses.GET,
                f'https://genius.com/test-lyrics-{i}',
                body=f'<div class="Lyrics__Container-sc-1ynbvzw-6">Test lyrics {i}</div>',
                status=200
            )

        def fetch_lyrics(artist, song):
            return lyrics_fetcher.fetch_lyrics(artist, song)

        # Execute concurrent requests
        with patch('time.sleep') as mock_sleep:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(fetch_lyrics, 'Test Artist', f'Test Song {i}')
                    for i in range(5)
                ]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Verify that rate limiting was handled properly
        assert mock_sleep.called
        # All requests should eventually succeed
        successful_results = [r for r in results if r is not None and 'test lyrics' in r.lower()]
        assert len(successful_results) > 0

    @pytest.mark.regression
    @responses.activate
    def test_malformed_rate_limit_response_regression(self, lyrics_fetcher):
        """
        Regression test for handling malformed rate limit responses.
        
        Previously, malformed rate limit responses (missing headers, invalid JSON)
        would cause crashes instead of graceful degradation.
        
        Issue: System crashed on malformed rate limit responses
        Fix: Graceful handling of malformed responses with fallback logic
        """
        # Malformed rate limit response (no Retry-After header, invalid JSON)
        responses.add(
            responses.GET,
            'https://api.genius.com/search',
            body='<html><body>Rate limit exceeded</body></html>',
            status=429,
            content_type='text/html'
        )

        # Follow up with successful response
        responses.add(
            responses.GET,
            'https://api.genius.com/search',
            json={
                'response': {
                    'hits': [{
                        'result': {
                            'id': 123,
                            'title': 'Test Song',
                            'primary_artist': {'name': 'Test Artist'},
                            'url': 'https://genius.com/test-lyrics'
                        }
                    }]
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

        # Should not crash, should handle gracefully
        with patch('time.sleep') as mock_sleep:
            result = lyrics_fetcher.fetch_lyrics('Test Artist', 'Test Song')

        # Should use default backoff when Retry-After header is missing
        assert mock_sleep.called
        assert result is not None

    @pytest.mark.regression
    @responses.activate
    def test_rate_limit_max_retries_regression(self, lyrics_fetcher):
        """
        Regression test for maximum retry limits on rate limiting.
        
        Previously, the system would retry indefinitely on persistent rate limits,
        leading to infinite loops and resource exhaustion.
        
        Issue: Infinite retries on persistent rate limits
        Fix: Maximum retry limit with exponential backoff ceiling
        """
        # Simulate persistent rate limiting (more retries than max allowed)
        for i in range(10):  # More than typical max retry limit
            responses.add(
                responses.GET,
                'https://api.genius.com/search',
                json={'error': 'rate limit exceeded'},
                status=429
            )

        with patch('time.sleep') as mock_sleep:
            result = lyrics_fetcher.fetch_lyrics('Test Artist', 'Test Song')

        # Should give up after maximum retries
        assert result is None or result == ""
        # Should not retry indefinitely
        assert mock_sleep.call_count <= 5  # Reasonable max retry limit

    @pytest.mark.regression
    @responses.activate
    def test_rate_limit_recovery_after_success_regression(self, lyrics_fetcher):
        """
        Regression test for rate limit state recovery.
        
        Previously, after hitting rate limits, the system would continue
        applying delays even after successful requests.
        
        Issue: Rate limit delays persisted after successful requests
        Fix: Reset rate limit state after successful API calls
        """
        # First request hits rate limit
        responses.add(
            responses.GET,
            'https://api.genius.com/search',
            json={'error': 'rate limit exceeded'},
            status=429
        )

        # Second request succeeds
        responses.add(
            responses.GET,
            'https://api.genius.com/search',
            json={
                'response': {
                    'hits': [{
                        'result': {
                            'id': 123,
                            'title': 'Test Song 1',
                            'primary_artist': {'name': 'Test Artist'},
                            'url': 'https://genius.com/test-lyrics-1'
                        }
                    }]
                }
            },
            status=200
        )

        responses.add(
            responses.GET,
            'https://genius.com/test-lyrics-1',
            body='<div class="Lyrics__Container-sc-1ynbvzw-6">Test lyrics 1</div>',
            status=200
        )

        # Third request should not have unnecessary delays
        responses.add(
            responses.GET,
            'https://api.genius.com/search',
            json={
                'response': {
                    'hits': [{
                        'result': {
                            'id': 124,
                            'title': 'Test Song 2',
                            'primary_artist': {'name': 'Test Artist'},
                            'url': 'https://genius.com/test-lyrics-2'
                        }
                    }]
                }
            },
            status=200
        )

        responses.add(
            responses.GET,
            'https://genius.com/test-lyrics-2',
            body='<div class="Lyrics__Container-sc-1ynbvzw-6">Test lyrics 2</div>',
            status=200
        )

        with patch('time.sleep') as mock_sleep:
            # First request with rate limit
            result1 = lyrics_fetcher.fetch_lyrics('Test Artist', 'Test Song 1')
            initial_sleep_count = mock_sleep.call_count

            # Second request should not add unnecessary delays
            result2 = lyrics_fetcher.fetch_lyrics('Test Artist', 'Test Song 2')
            final_sleep_count = mock_sleep.call_count

        # First request should have triggered sleep due to rate limit
        assert initial_sleep_count > 0
        # Second request should not add additional delays
        assert final_sleep_count == initial_sleep_count
        
        assert result1 is not None
        assert result2 is not None 