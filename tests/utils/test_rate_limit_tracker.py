"""
Tests for RateLimitTracker class
"""
import pytest
import time
from unittest.mock import patch, Mock
from app.utils.lyrics import RateLimitTracker


class TestRateLimitTracker:
    """Test suite for RateLimitTracker class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.tracker = RateLimitTracker(window_size=60, max_requests=50)
    
    def test_can_make_request_when_empty(self):
        """Test that requests are allowed when tracker is empty"""
        assert self.tracker.can_make_request() is True
    
    def test_record_request_updates_timestamp_list(self):
        """Test that recording a request adds to timestamp list"""
        initial_count = len(self.tracker.request_timestamps)
        self.tracker.record_request()
        assert len(self.tracker.request_timestamps) == initial_count + 1
    
    def test_can_make_request_under_limit(self):
        """Test that requests are allowed when under the limit"""
        # Record 49 requests (under limit of 50)
        for _ in range(49):
            self.tracker.record_request()
        
        assert self.tracker.can_make_request() is True
    
    def test_can_make_request_at_limit(self):
        """Test that requests are denied when at the limit"""
        # Record max_requests (50) requests
        for _ in range(50):
            self.tracker.record_request()
        
        assert self.tracker.can_make_request() is False
    
    def test_can_make_request_over_limit(self):
        """Test that requests are denied when over the limit"""
        # Record more than max_requests
        for _ in range(55):
            self.tracker.record_request()
        
        assert self.tracker.can_make_request() is False
    
    @patch('app.utils.lyrics.time.time')
    def test_window_sliding_removes_old_requests(self, mock_time):
        """Test that old requests outside the window are removed"""
        # Set initial time
        mock_time.return_value = 1000.0
        
        # Record max requests at time 1000
        for _ in range(50):
            self.tracker.record_request()
        
        # Should be at limit
        assert self.tracker.can_make_request() is False
        
        # Move time forward beyond window (61 seconds)
        mock_time.return_value = 1061.0
        
        # Old requests should be removed, allowing new ones
        assert self.tracker.can_make_request() is True
    
    @patch('app.utils.lyrics.time.time')
    def test_window_sliding_partial_removal(self, mock_time):
        """Test that only requests outside window are removed"""
        # Record 25 requests at time 1000
        mock_time.return_value = 1000.0
        for _ in range(25):
            self.tracker.record_request()
        
        # Record 25 more requests at time 1030 (30 seconds later)
        mock_time.return_value = 1030.0
        for _ in range(25):
            self.tracker.record_request()
        
        # Should be at limit (50 requests)
        assert self.tracker.can_make_request() is False
        
        # Move to time 1070 (40 seconds after second batch)
        # First batch (at 1000) should be removed (70 seconds old)
        # Second batch (at 1030) should remain (40 seconds old)
        mock_time.return_value = 1070.0
        
        # Should allow requests again (only 25 in window)
        assert self.tracker.can_make_request() is True
    
    def test_custom_window_size(self):
        """Test tracker with custom window size"""
        tracker = RateLimitTracker(window_size=30, max_requests=10)
        
        # Should allow requests initially
        assert tracker.can_make_request() is True
        
        # Fill to limit
        for _ in range(10):
            tracker.record_request()
        
        # Should deny requests at limit
        assert tracker.can_make_request() is False
    
    def test_custom_max_requests(self):
        """Test tracker with custom max requests"""
        tracker = RateLimitTracker(window_size=60, max_requests=5)
        
        # Record up to limit
        for _ in range(5):
            tracker.record_request()
        
        # Should deny further requests
        assert tracker.can_make_request() is False
    
    @patch('app.utils.lyrics.time.time')
    def test_get_request_count_in_window(self, mock_time):
        """Test getting current request count in window"""
        mock_time.return_value = 1000.0
        
        # Record some requests
        for _ in range(10):
            self.tracker.record_request()
        
        # Get count (this method we'll implement)
        count = self.tracker.get_current_request_count()
        assert count == 10
        
        # Move time forward to remove some requests
        mock_time.return_value = 1070.0  # 70 seconds later
        
        # Should show 0 requests in current window
        count = self.tracker.get_current_request_count()
        assert count == 0
    
    def test_reset_tracker(self):
        """Test resetting the tracker"""
        # Add some requests
        for _ in range(20):
            self.tracker.record_request()
        
        assert len(self.tracker.request_timestamps) == 20
        
        # Reset tracker
        self.tracker.reset()
        
        assert len(self.tracker.request_timestamps) == 0
        assert self.tracker.can_make_request() is True
    
    @patch('app.utils.lyrics.time.time')
    def test_time_until_next_request_available(self, mock_time):
        """Test calculating time until next request is available"""
        mock_time.return_value = 1000.0
        
        # Fill to limit
        for _ in range(50):
            self.tracker.record_request()
        
        # Should return time until oldest request expires
        time_until = self.tracker.time_until_next_available()
        
        # Should be close to window_size (60 seconds)
        assert 59 <= time_until <= 60 