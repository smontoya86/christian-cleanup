"""
Tests for LyricsFetcher rate limit detection methods
"""

from app.utils.lyrics import LyricsFetcher


class MockResponse:
    """Mock HTTP response for testing"""

    def __init__(self, status_code, headers=None):
        self.status_code = status_code
        self.headers = headers or {}


class TestLyricsFetcherRateDetection:
    """Test suite for LyricsFetcher rate limit detection"""

    def setup_method(self):
        """Set up test fixtures"""
        self.fetcher = LyricsFetcher()

    def test_is_rate_limited_detects_429_status(self):
        """Test that 429 status code is detected as rate limited"""
        response = MockResponse(status_code=429)
        assert self.fetcher.is_rate_limited(response) is True

    def test_is_rate_limited_ignores_200_status(self):
        """Test that 200 status code is not detected as rate limited"""
        response = MockResponse(status_code=200)
        assert self.fetcher.is_rate_limited(response) is False

    def test_is_rate_limited_detects_zero_remaining_header(self):
        """Test detection via X-RateLimit-Remaining header"""
        response = MockResponse(status_code=200, headers={"X-RateLimit-Remaining": "0"})
        assert self.fetcher.is_rate_limited(response) is True

    def test_is_rate_limited_allows_positive_remaining_header(self):
        """Test that positive remaining count is not rate limited"""
        response = MockResponse(status_code=200, headers={"X-RateLimit-Remaining": "10"})
        assert self.fetcher.is_rate_limited(response) is False

    def test_is_rate_limited_handles_invalid_header_values(self):
        """Test that invalid header values don't crash"""
        response = MockResponse(status_code=200, headers={"X-RateLimit-Remaining": "invalid"})
        assert self.fetcher.is_rate_limited(response) is False

    def test_is_rate_limited_checks_multiple_header_formats(self):
        """Test detection with different header name formats"""
        header_formats = [
            "X-RateLimit-Remaining",
            "X-Rate-Limit-Remaining",
            "RateLimit-Remaining",
            "Rate-Limit-Remaining",
        ]

        for header in header_formats:
            response = MockResponse(status_code=200, headers={header: "0"})
            assert self.fetcher.is_rate_limited(response) is True

    def test_is_rate_limited_handles_missing_headers(self):
        """Test behavior when response has no rate limit headers"""
        response = MockResponse(status_code=200, headers={"Content-Type": "application/json"})
        assert self.fetcher.is_rate_limited(response) is False

    def test_is_rate_limited_handles_object_without_attributes(self):
        """Test behavior with objects that don't have expected attributes"""
        response = object()  # Plain object with no attributes
        assert self.fetcher.is_rate_limited(response) is False

    def test_is_approaching_rate_limit_default_threshold(self):
        """Test approaching rate limit with default 80% threshold"""
        # Fill tracker to 80% (48 out of 60 requests)
        for _ in range(48):
            self.fetcher.rate_tracker.record_request()

        assert self.fetcher.is_approaching_rate_limit() is True

    def test_is_approaching_rate_limit_below_threshold(self):
        """Test not approaching rate limit when below threshold"""
        # Fill tracker to 70% (42 out of 60 requests)
        for _ in range(42):
            self.fetcher.rate_tracker.record_request()

        assert self.fetcher.is_approaching_rate_limit() is False

    def test_is_approaching_rate_limit_custom_threshold(self):
        """Test approaching rate limit with custom threshold"""
        # Fill tracker to 50% (30 out of 60 requests)
        for _ in range(30):
            self.fetcher.rate_tracker.record_request()

        # Should not be approaching with default 80% threshold
        assert self.fetcher.is_approaching_rate_limit() is False

        # Should be approaching with 50% threshold
        assert self.fetcher.is_approaching_rate_limit(threshold=0.5) is True

    def test_is_approaching_rate_limit_at_limit(self):
        """Test approaching when at the rate limit"""
        # Fill tracker to maximum (60 out of 60 requests)
        for _ in range(60):
            self.fetcher.rate_tracker.record_request()

        assert self.fetcher.is_approaching_rate_limit() is True

    def test_is_approaching_rate_limit_empty_tracker(self):
        """Test not approaching when tracker is empty"""
        assert self.fetcher.is_approaching_rate_limit() is False

    def test_get_cache_stats_includes_rate_info(self):
        """Test that cache stats include rate limiting information"""
        # Add some requests to tracker
        for _ in range(25):
            self.fetcher.rate_tracker.record_request()

        stats = self.fetcher.get_cache_stats()

        assert "api_calls_this_minute" in stats
        assert "rate_limit_remaining" in stats
        assert stats["api_calls_this_minute"] == 25
        assert stats["rate_limit_remaining"] == 35  # 60 - 25

    def test_get_cache_stats_includes_token_bucket_info(self):
        """Test that cache stats include token bucket information"""
        # Consume some tokens
        self.fetcher.token_bucket.consume(3)

        stats = self.fetcher.get_cache_stats()

        assert "tokens_available" in stats
        assert "token_bucket_capacity" in stats
        assert (
            "cache_size" in stats
        )  # New database-based cache uses cache_size instead of cache_valid_entries
        assert (
            "cache_sources" in stats
        )  # New implementation includes cache_sources instead of expired entries
        assert stats["tokens_available"] == 7  # 10 - 3 consumed
        assert stats["token_bucket_capacity"] == 10

    def test_token_bucket_throttling_integration(self):
        """Test that token bucket is properly integrated into rate limiting"""
        # Consume all tokens
        self.fetcher.token_bucket.consume(10)

        # Verify no tokens available
        assert self.fetcher.token_bucket.get_available_tokens() == 0

        # The _respect_rate_limit method should handle this gracefully
        # We can't easily test the sleep behavior without mocking time,
        # but we can verify the token bucket is being used
        assert hasattr(self.fetcher, "token_bucket")
        assert self.fetcher.token_bucket.capacity == 10
