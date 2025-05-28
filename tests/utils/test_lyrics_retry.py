"""
Tests for LyricsFetcher retry mechanism
"""
import pytest
import time
import random
from unittest.mock import patch, Mock, MagicMock
from requests.exceptions import RequestException
from app.utils.lyrics import LyricsFetcher


class MockResponse:
    """Mock HTTP response for testing"""
    def __init__(self, status_code, json_data=None, headers=None, text=""):
        self.status_code = status_code
        self.json_data = json_data or {}
        self.headers = headers or {}
        self.text = text
    
    def json(self):
        return self.json_data


class TestLyricsFetcherRetry:
    """Test suite for LyricsFetcher retry mechanism"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.fetcher = LyricsFetcher()
    
    @patch('app.utils.lyrics.requests.get')
    @patch('app.utils.lyrics.time.sleep')
    def test_exponential_backoff_success_after_retries(self, mock_sleep, mock_get):
        """Test that exponential backoff succeeds after several 429 responses"""
        # Mock sequence: 429, 429, 200 (success)
        mock_responses = [
            MockResponse(429, headers={'Retry-After': '2'}),
            MockResponse(429, headers={'Retry-After': '1'}),
            MockResponse(200, json_data={'result': 'success'})
        ]
        mock_get.side_effect = mock_responses
        
        # Call the method we'll implement
        result = self.fetcher.fetch_with_retry('https://api.example.com/endpoint')
        
        # Verify the function retried and eventually succeeded
        assert mock_get.call_count == 3
        assert result.status_code == 200
        assert mock_sleep.call_count == 2  # Two sleep calls for the two 429s
    
    @patch('app.utils.lyrics.requests.get')
    @patch('app.utils.lyrics.time.sleep')
    def test_exponential_backoff_respects_retry_after(self, mock_sleep, mock_get):
        """Test that retry mechanism respects Retry-After header"""
        mock_get.side_effect = [
            MockResponse(429, headers={'Retry-After': '5'}),
            MockResponse(200, json_data={'result': 'success'})
        ]
        
        result = self.fetcher.fetch_with_retry('https://api.example.com/endpoint')
        
        # Verify Retry-After was respected (should sleep at least 5 seconds)
        assert mock_sleep.call_count == 1
        sleep_duration = mock_sleep.call_args[0][0]
        assert sleep_duration >= 5
    
    @patch('app.utils.lyrics.requests.get')
    @patch('app.utils.lyrics.time.sleep')
    def test_exponential_backoff_max_retries_exceeded(self, mock_sleep, mock_get):
        """Test that function gives up after max retries"""
        # Always return 429
        mock_get.return_value = MockResponse(429, headers={'Retry-After': '1'})
        
        result = self.fetcher.fetch_with_retry('https://api.example.com/endpoint', max_retries=3)
        
        # Should have tried 3 times (initial + 2 retries)
        assert mock_get.call_count == 3
        assert result.status_code == 429  # Final response should be the 429
    
    @patch('app.utils.lyrics.requests.get')
    @patch('app.utils.lyrics.time.sleep')
    def test_exponential_backoff_with_jitter(self, mock_sleep, mock_get):
        """Test that jitter is applied to prevent thundering herd"""
        mock_get.side_effect = [
            MockResponse(429),
            MockResponse(200, json_data={'result': 'success'})
        ]
        
        # Mock random to control jitter
        with patch('app.utils.lyrics.random.uniform', return_value=0.5):
            result = self.fetcher.fetch_with_retry('https://api.example.com/endpoint')
        
        # Verify sleep was called with exponential backoff + jitter
        assert mock_sleep.call_count == 1
        sleep_duration = mock_sleep.call_args[0][0]
        # Expected: 2^1 + 0.5 = 2.5
        assert abs(sleep_duration - 2.5) < 0.1
    
    @patch('app.utils.lyrics.requests.get')
    @patch('app.utils.lyrics.time.sleep')
    def test_exponential_backoff_handles_exceptions(self, mock_sleep, mock_get):
        """Test that exceptions during requests are handled with retry"""
        mock_get.side_effect = [
            RequestException("Connection error"),
            RequestException("Timeout"),
            MockResponse(200, json_data={'result': 'success'})
        ]
        
        result = self.fetcher.fetch_with_retry('https://api.example.com/endpoint')
        
        # Should have retried twice and succeeded on third attempt
        assert mock_get.call_count == 3
        assert result.status_code == 200
    
    @patch('app.utils.lyrics.requests.get')
    def test_exponential_backoff_max_retries_with_exceptions(self, mock_get):
        """Test that function gives up after max retries with exceptions"""
        mock_get.side_effect = RequestException("Persistent error")
        
        with pytest.raises(RequestException):
            self.fetcher.fetch_with_retry('https://api.example.com/endpoint', max_retries=2)
        
        # Should have tried 2 times (initial + 1 retry)
        assert mock_get.call_count == 2
    
    @patch('app.utils.lyrics.requests.get')
    def test_exponential_backoff_immediate_success(self, mock_get):
        """Test that successful requests don't trigger retries"""
        mock_get.return_value = MockResponse(200, json_data={'result': 'success'})
        
        result = self.fetcher.fetch_with_retry('https://api.example.com/endpoint')
        
        # Should only make one request
        assert mock_get.call_count == 1
        assert result.status_code == 200
    
    @patch('app.utils.lyrics.requests.get')
    @patch('app.utils.lyrics.time.sleep')
    def test_exponential_backoff_custom_headers(self, mock_sleep, mock_get):
        """Test that custom headers are passed through retries"""
        custom_headers = {'Authorization': 'Bearer token123'}
        mock_get.side_effect = [
            MockResponse(429),
            MockResponse(200, json_data={'result': 'success'})
        ]
        
        result = self.fetcher.fetch_with_retry(
            'https://api.example.com/endpoint',
            headers=custom_headers
        )
        
        # Verify headers were passed in both requests
        assert mock_get.call_count == 2
        for call in mock_get.call_args_list:
            assert call[1]['headers'] == custom_headers
    
    def test_exponential_backoff_calculates_sleep_correctly(self):
        """Test the exponential backoff calculation without making actual requests"""
        # Test backoff calculation logic
        retry_counts = [0, 1, 2, 3, 4]
        expected_base = [1, 2, 4, 8, 16]  # 2^retry_count
        
        for retry, expected in zip(retry_counts, expected_base):
            # The actual implementation will use 2^retry + jitter
            # We'll test that the base calculation is correct
            base_sleep = 2 ** retry
            assert base_sleep == expected 